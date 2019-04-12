from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import viewsets, response, status, exceptions, permissions, mixins
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from . import exceptions as app_exceptions, serializers as app_serializers, filters as app_filters, statistics
from . import permissions as app_permissions, models as app_models, enums, services, relations as app_relations
from AnimationBoard.settings import COVER_DIRS
from PIL import Image
import os
import uuid


class User:
    class Login(viewsets.ViewSet):
        @staticmethod
        def create(request):
            if request.user.is_authenticated:
                raise app_exceptions.AlreadyLogin()
            data = request.data
            app_serializers.User.Login(data=data).is_valid(raise_exception=True)
            username = data['username']
            password = data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                user.profile.last_login_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
                user.profile.last_login_time = timezone.now()
                user.profile.save()
                return response.Response(status=status.HTTP_200_OK)
            else:
                raise exceptions.AuthenticationFailed()

    class Token(viewsets.ViewSet):
        @staticmethod
        def create(request):
            if request.user.is_authenticated:
                raise app_exceptions.AlreadyLogin()
            data = request.data
            app_serializers.User.Login(data=data).is_valid(raise_exception=True)
            username = data['username']
            password = data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                token, created = Token.objects.get_or_create(user=user)
                user.profile.last_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
                user.profile.last_login = timezone.now()
                user.profile.save()
                return response.Response({'token': token.key}, status=status.HTTP_200_OK)
            raise exceptions.AuthenticationFailed()

    class RefreshToken(viewsets.ViewSet):
        @staticmethod
        def create(request):
            if request.user.is_authenticated and request.user.is_superuser:
                data = request.data
                username = data.get('username', None)
                user = app_models.User.objects.filter(username=username).first()
                if user is not None:
                    token, created = Token.objects.get_or_create(user=user)
                    if not created:
                        token.delete()
                        Token.objects.create(user=user)
                    return response.Response(status=status.HTTP_200_OK)
                else:
                    return response.Response({'code': 'UserNotFound', 'detail': 'user is not found.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                raise exceptions.AuthenticationFailed()

    class Logout(viewsets.ViewSet):
        permission_classes = (permissions.IsAuthenticated,)

        @staticmethod
        def create(request):
            logout(request)
            return response.Response(status=status.HTTP_200_OK)

    class Register(viewsets.ViewSet):
        @staticmethod
        def create(request):
            if request.user.is_authenticated:
                raise app_exceptions.AlreadyLogin()
            data = request.data
            app_serializers.User.Register(data=data).is_valid(raise_exception=True)
            username = data['username']
            name = data['name']
            password = data['password']
            registration_code = data['registration_code']
            if app_models.User.objects.filter(username=username).exists():
                raise app_exceptions.ApiError('UserExists', 'Username is already exist.')
            elif registration_code is not None:
                if services.Setting.setting().register_mode == enums.GlobalSettingRegisterMode.close:
                    raise app_exceptions.ApiError('CodeForbidden',
                                                  'Register by registration key was forbidden by admin.',
                                                  status.HTTP_403_FORBIDDEN)
                if app_models.RegistrationCode.objects.filter(code=registration_code, enable=True).exists():
                    key = app_models.RegistrationCode.objects.filter(code=registration_code, enable=True).first()
                    key.enable = False
                    if key.deadline is not None and key.deadline < timezone.now():
                        app_models.RegistrationCode.save(key)
                        raise app_exceptions.ApiError('WrongKey', 'Wrong registration key.')
                    profile = services.Profile.create_full_user(username=username, name=name, password=password,
                                                                is_staff=False, is_superuser=False,
                                                                create_path=enums.ProfileCreatePath.activate)
                    key.used_user = profile.username
                    key.used_time = timezone.now()
                    app_models.RegistrationCode.save(key)
                    login(request, profile.user)
                    if 'HTTP_X_FORWARDED_FOR' in request.META:
                        profile.last_ip = request.META['HTTP_X_FORWARDED_FOR']
                    else:
                        profile.last_ip = request.META['REMOTE_ADDR']
                    profile.last_login = timezone.now()
                    profile.save()
                    return response.Response(status=status.HTTP_200_OK)
                else:
                    raise app_exceptions.ApiError('WrongKey', 'Wrong registration key.')
            else:
                if services.Setting.setting().register_mode != enums.GlobalSettingRegisterMode.open:
                    raise app_exceptions.ApiError('RegisterForbidden', 'Register was forbidden by admin.',
                                                  status.HTTP_403_FORBIDDEN)
                profile = services.Profile.create_full_user(username=username, name=name, password=password,
                                                            is_staff=False, is_superuser=False,
                                                            create_path=enums.ProfileCreatePath.register)
                login(request, profile.user)
                if 'HTTP_X_FORWARDED_FOR' in request.META:
                    profile.last_ip = request.META['HTTP_X_FORWARDED_FOR']
                else:
                    profile.last_ip = request.META['REMOTE_ADDR']
                profile.last_login = timezone.now()
                profile.save()
                return response.Response(status=status.HTTP_200_OK)
            pass


class Cover:
    @staticmethod
    def split_filename(filename):
        p = filename.rfind('.')
        if p >= 0:
            return filename[:p], filename[p + 1:]
        else:
            return filename, ''

    @staticmethod
    def analyse_image(in_path, out_path, size=384):
        img = Image.open(in_path)
        # 裁剪成正方形
        width, height = img.size
        if width > height:
            img = img.crop(((width - height) / 2, 0, (width + height) / 2, height))
        elif width < height:
            img = img.crop((0, (height - width) / 2, width, (height + width) / 2))
        # 压缩到极小的尺寸
        img.thumbnail((size, size))
        img.convert('RGB').save(out_path)
        os.remove(in_path)

    class Animation(viewsets.ViewSet):
        permission_classes = (app_permissions.IsStaff,)

        @staticmethod
        def create(request):
            index = request.POST.get('id')
            res = app_models.Animation.objects.filter(id=index).first()
            if res is None:
                return response.Response(status=404)
            file = request.FILES.get('cover')
            name, ext = Cover.split_filename(file.name)
            content_type = file.content_type
            # 文件类型不对时返回400
            if content_type[:5] != 'image':
                return response.Response(status=400)
            # 删除旧的文件
            if res.cover is not None:
                old_path = '%s/%s' % (COVER_DIRS, res.cover)
                if os.path.exists(old_path):
                    os.remove(old_path)
                res.cover = None
            # 计算新文件名和新文件路径
            new_cover_name = '%s-%s-%s.%s' % ('animation', res.id, uuid.uuid4(), 'jpg')
            new_path = '%s/%s' % (COVER_DIRS, new_cover_name)
            # 将文件名保存下来
            res.cover = new_cover_name
            res.save()
            # 将文件名扩散到所有的缓存
            app_relations.spread_cache_field(res.id, res.relations,
                                         lambda id_list: app_models.Animation.objects.filter(id__in=id_list).all(),
                                         'cover', new_cover_name)
            # 存储路径不存在时先创建路径
            if not os.path.exists(COVER_DIRS):
                os.makedirs(COVER_DIRS)
            # 该文件万一已经存在，就删除文件
            if os.path.exists(new_path):
                os.remove(new_path)
            # 将图像写入到一个临时的文件
            temp_path = '%s/temp-%s-%s.%s' % (COVER_DIRS, 'animation', uuid.uuid4(), ext)
            with open(temp_path, 'wb') as f:
                for c in file.chunks():
                    f.write(c)
            # 处理这张图片，对其进行裁切和缩放
            Cover.analyse_image(temp_path, new_path)
            return response.Response({'cover': new_cover_name}, status=201)

    class Profile(viewsets.ViewSet):
        @staticmethod
        def create(request):
            index = request.data.get('id')
            res = app_models.Profile.objects.filter(username=index).first()
            if res is None:
                return response.Response(status=404)
            if not app_permissions.SelfOnly().has_object_permission(request, None, res):
                return response.Response(status=403)
            file = request.FILES.get('cover')
            name, ext = Cover.split_filename(file.name)
            content_type = file.content_type
            # 文件类型不对时返回400
            if content_type[:5] != 'image':
                return HttpResponse(status=400)
            # 删除旧的文件
            if res.cover is not None:
                old_path = '%s/%s' % (COVER_DIRS, res.cover)
                if os.path.exists(old_path):
                    os.remove(old_path)
                res.cover = None
            # 计算新文件名和新文件路径
            new_cover_name = '%s-%s-%s.%s' % ('profile', res.id, uuid.uuid4(), 'jpg')
            new_path = '%s/%s' % (COVER_DIRS, new_cover_name)
            # 将文件名保存下来
            res.cover = new_cover_name
            res.save()
            # 存储路径不存在时先创建路径
            if not os.path.exists(COVER_DIRS):
                os.makedirs(COVER_DIRS)
            # 该文件万一已经存在，就删除文件
            if os.path.exists(new_path):
                os.remove(new_path)
            # 将图像写入到一个临时的文件
            temp_path = '%s/temp-%s-%s.%s' % (COVER_DIRS, 'profile', uuid.uuid4(), ext)
            with open(temp_path, 'wb') as f:
                for c in file.chunks():
                    f.write(c)
            # 处理这张图片，对其进行裁切和缩放
            Cover.analyse_image(temp_path, new_path)
            return response.Response({'cover': new_cover_name}, status=201)


class Profile:
    class Info(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = app_models.Profile.objects.all()
        serializer_class = app_serializers.Profile.Info
        permission_classes = (app_permissions.SelfOnly,)
        lookup_field = 'username'

        def list(self, request, *args, **kwargs):
            profile = request.user.profile
            self.kwargs['username'] = profile.username
            return self.retrieve(request, *args, **kwargs)

    class Password(mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = app_models.User.objects.all()
        serializer_class = app_serializers.Profile.Password
        permission_classes = (app_permissions.SelfOnly,)
        lookup_field = 'username'

        def list(self, request, *args, **kwargs):
            profile = request.user.profile
            return redirect('api-profile-password-detail', username=profile.username)

        def update(self, request, *args, **kwargs):
            serializer = self.get_serializer(data=request.data, partial=False)
            serializer.is_valid(raise_exception=True)
            old_password = request.data['old_password']
            new_password = request.data['new_password']
            user = self.get_object()
            if authenticate(username=user.username, password=old_password) is not None:
                user.set_password(new_password)
                user.save()
                return response.Response(status=status.HTTP_200_OK)
            else:
                raise exceptions.AuthenticationFailed()

    class Message(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = app_models.Message.objects
        serializer_class = app_serializers.Profile.Message
        permission_classes = (app_permissions.SelfOnly,)
        lookup_field = 'id'
        filter_fields = ('read', 'type')
        ordering_fields = ('id', 'read', 'type', 'create_time')
        ordering = '-create_time'

        def get_queryset(self):
            profile = self.request.user.profile
            queryset = self.queryset.filter(owner=profile)
            return queryset

        @action(detail=False, methods=['GET'])
        def unread_count(self, request):
            count = self.get_queryset().filter(read=False).count()
            return response.Response({'count': count})


class Database:
    class Animation(viewsets.ModelViewSet):
        queryset = app_models.Animation.objects
        serializer_class = app_serializers.Database.Animation
        permission_classes = (app_permissions.IsStaffOrReadOnly,)
        lookup_field = 'id'
        filterset_class = app_filters.Database.Animation
        search_fields = ('title', 'origin_title', 'other_title', 'tags__name', 'keyword',
                         'staff_companies__name', 'staff_supervisors__name', 'original_work_authors__name')
        ordering_fields = ('id', 'title', 'original_work_type', 'publish_type', 'limit_level', 'publish_time', 'create_time', 'update_time')

        def perform_create(self, serializer):
            serializer.validated_data['creator'] = self.request.user.username
            super().perform_create(serializer)

        def perform_update(self, serializer):
            serializer.validated_data['updater'] = self.request.user.username
            super().perform_update(serializer)
            if hasattr(serializer.instance, 'diaries'):
                diaries = serializer.instance.diaries.all()
                sum_quantity = serializer.instance.sum_quantity
                now = timezone.now()
                for diary in diaries:
                    if diary.status != enums.DiaryStatus.give_up:
                        if sum_quantity is None:
                            diary.status = enums.DiaryStatus.ready
                        elif diary.watched_quantity >= sum_quantity:
                            diary.status = enums.DiaryStatus.complete
                            if diary.finish_time is None:
                                diary.finish_time = now
                        else:
                            diary.status = enums.DiaryStatus.watching
                            if diary.finish_time is not None:
                                diary.finish_time = None
                    diary.save()

        def perform_destroy(self, instance):
            app_relations.remove_cache_instance(instance.id, instance.relations, lambda id_list: app_models.Animation.objects.filter(id__in=id_list).all())
            super().perform_destroy(instance)

    class Staff(viewsets.ModelViewSet):
        queryset = app_models.Staff.objects
        serializer_class = app_serializers.Database.Staff
        permission_classes = (app_permissions.IsStaffOrReadOnly,)
        lookup_field = 'id'
        filter_fields = ('is_organization',)
        search_fields = ('name', 'origin_name', 'remark')
        ordering_fields = ('id', 'name', 'create_time', 'update_time')

        def perform_create(self, serializer):
            serializer.validated_data['creator'] = self.request.user.username
            super().perform_create(serializer)

        def perform_update(self, serializer):
            serializer.validated_data['updater'] = self.request.user.username
            super().perform_update(serializer)

    class Tag(viewsets.ModelViewSet):
        queryset = app_models.Tag.objects
        serializer_class = app_serializers.Database.Tag
        permission_classes = (app_permissions.IsStaffOrReadOnly,)
        lookup_field = 'name'
        filter_fields = ('name',)
        search_fields = ('name', 'introduction')
        ordering_fields = ('id', 'name', 'create_time', 'update_time')

        def perform_create(self, serializer):
            serializer.validated_data['creator'] = self.request.user.username
            super().perform_create(serializer)

        def perform_update(self, serializer):
            serializer.validated_data['updater'] = self.request.user.username
            super().perform_update(serializer)


class Personal:
    class Diary(viewsets.ModelViewSet):
        queryset = app_models.Diary.objects
        serializer_class = app_serializers.Personal.Diary
        permission_classes = (app_permissions.SelfOnly,)
        lookup_field = 'animation_id'
        filterset_class = app_filters.Personal.Diary
        search_fields = ('title',)
        ordering_fields = ('id', 'title', 'watched_quantity', 'sum_quantity', 'published_quantity', 'status',
                           'create_time', 'update_time', 'finish_time')

        def get_queryset(self):
            return self.queryset.filter(owner=self.request.user.profile).all()

    class Comment(viewsets.ModelViewSet):
        queryset = app_models.Comment.objects
        serializer_class = app_serializers.Personal.Comment
        permission_classes = (app_permissions.SelfOnly,)
        lookup_field = 'animation_id'
        filterset_class = app_filters.Personal.Comment
        search_fields = ('short_comment', 'article', 'animation__title')
        ordering_fields = ('id', 'animation__title', 'score', 'create_time', 'update_time')

        def get_queryset(self):
            return self.queryset.filter(owner=self.request.user.profile).all()


class Statistics(viewsets.ViewSet):
    serializer_class = app_serializers.Statistics
    permission_classes = (app_permissions.IsLogin,)

    @staticmethod
    def list(request):
        return Statistics.action(request, False)

    @staticmethod
    def create(request):
        return Statistics.action(request, True)

    @staticmethod
    def action(request, create):
        def get_parameter(field, translate=None):
            if field not in request.query_params:
                raise app_exceptions.ApiError('RequireParameter', 'parameter "%s" is required.' % (field,))
            result = request.query_params[field]
            if translate is not None:
                try:
                    return translate(result)
                except Exception:
                    raise app_exceptions.ApiError('WrongParameterType',
                                                  'parameter "%s" cannot be translated to correct type.' % (field,))
            return result
        if 'type' not in request.query_params:
            raise app_exceptions.ApiError('NoType', 'parameter "type" is required.')
        tp = request.query_params['type']
        profile = request.user.profile
        if tp == services.Statistics.OVERVIEW:
            model = services.Statistics.overview(profile, create)
        elif tp == services.Statistics.SEASON_TABLE:
            model = services.Statistics.season_table(profile,
                                                     get_parameter('year', lambda i: int(i)),
                                                     get_parameter('season', lambda i: int(i)),
                                                     create)
        elif tp == services.Statistics.SEASON_CHART:
            model = services.Statistics.season_chart(profile, create)
        elif tp == services.Statistics.TIMELINE:
            model = services.Statistics.timeline(profile,
                                                 get_parameter('key', lambda key: key if key else None),
                                                 request.data if create else None)
        elif tp == services.Statistics.TIMELINE_RECORD:
            model = services.Statistics.timeline_record(profile)
        else:
            raise app_exceptions.ApiError('WrongType', 'unknown type "%s".' % (tp,))
        if model is None:
            return response.Response(status=status.HTTP_404_NOT_FOUND)
        serializer = Statistics.serializer_class(instance=model)
        return response.Response(serializer.data)


class Admin:
    class Setting(viewsets.ViewSet):
        serializer_class = app_serializers.Admin.Setting
        permission_classes = (app_permissions.IsStaff,)

        def list(self, request):
            serializer = self.serializer_class(instance=services.Setting.setting())
            return response.Response(serializer.data)

        def create(self, request):
            setting = services.Setting.setting()
            serializer = self.serializer_class(instance=setting, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return response.Response(serializer.data)

    class User(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = app_models.Profile.objects
        serializer_class = app_serializers.Admin.User
        permission_classes = (app_permissions.IsStaff,)
        lookup_field = 'username'
        filter_fields = ('user__is_staff', 'create_path')
        search_fields = ('username', 'name', 'last_login_ip')
        ordering_fields = ('create_path', 'create_time', 'last_login_time')

    class Permission(mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = app_models.Profile.objects
        serializer_class = app_serializers.Admin.Permission
        permission_classes = (app_permissions.Above,)
        lookup_field = 'username'

        def perform_update(self, serializer):
            if (not self.request.user.is_superuser) and ('is_staff' in serializer.validated_data):
                del serializer.validated_data['is_staff']
            super().perform_update(serializer)

    class RegistrationCode(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
        queryset = app_models.RegistrationCode.objects
        serializer_class = app_serializers.Admin.RegistrationCode
        permission_classes = (app_permissions.IsStaff,)
        lookup_field = 'id'
        filter_fields = ('enable',)
        ordering_fields = ('deadline', 'enable', 'used_time', 'create_time')

    class SystemMessage(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
        queryset = app_models.Message.objects.filter(type=enums.MessageType.system)
        serializer_class = app_serializers.Admin.SystemMessage
        permission_classes = (app_permissions.IsStaff,)
        lookup_field = 'id'
        filter_fields = ('read', 'owner__username')
        ordering_fields = ('read', 'owner', 'create_time')
        ordering = '-create_time'
