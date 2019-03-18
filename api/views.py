from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import viewsets, response, status, exceptions, permissions, mixins
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from . import exceptions as app_exceptions, serializers as app_serializers, filters as app_filters
from . import permissions as app_permissions, models as app_models, enums, services, utils
from AnimationBoard.settings import COVER_DIRS
from PIL import Image
import json
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
                user.profile.last_ip = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('REMOTE_ADDR')
                user.profile.last_login = timezone.now()
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
    """
    封面上传系统的逻辑说明：
    - 该系统设计上不止用于animation封面，扩展后也可用于用户头像等。
    - 该系统使用静态文件传送，同时避免缓存。

    上传逻辑：
    - 在资源的model有一个cover: string类型的字段。默认为null。
    - 使用/api/cover/{resource}/{id}/的url。
    - resource代表资源种类，如animation, profile。id是该资源的主键。
    - 图像资源在file中传递过来。
    - 拿到图像后，将关键信息保存在模型层的cover字段中。
        - 如果cover字段为null，那么，使用hash算法计算出一个hash值，将图像在storage文件夹下保存为{resource}-{id}-{hash}.{ext}。同时把这个名字记录到cover字段上。
        - 如果不为null，那么先删掉这个字段名所记录的文件，再执行保存。

    取用逻辑：
    - 要取用一项资源关联的cover，首先get资源，拿到cover字段。
    - cover字段不是null时，你就可以调取资源/static/cover/{cover}来请求这项资源。
    """
    @staticmethod
    def cover(request, target, index):
        if request.method == 'POST':
            if target == 'animation':
                try:
                    i = int(index)
                except ValueError:
                    return HttpResponse(status=404)
                return Cover.__post_animation(request, i)
            else:
                return HttpResponse(status=404)
        elif request.method == 'OPTIONS':
            return Cover.__options()
        else:
            return HttpResponse(status=405)

    @staticmethod
    def __post_animation(request, index):
        animation = app_models.Animation.objects.filter(id=index).first()
        if animation is None:
            return HttpResponse(status=404)
        file = request.FILES.get('cover')
        name, ext = Cover.__split_filename(file.name)
        content_type = file.content_type
        # 文件类型不对时返回400
        if content_type[:5] != 'image':
            return HttpResponse(status=400)
        # 删除旧的文件
        if animation.cover is not None:
            old_path = '%s/%s' % (COVER_DIRS, animation.cover)
            if os.path.exists(old_path):
                os.remove(old_path)
            animation.cover = None
        # 计算新文件名和新文件路径
        new_cover_name = 'animation-%s-%s.%s' % (animation.id, uuid.uuid4(), ext)
        new_path = '%s/%s' % (COVER_DIRS, new_cover_name)
        # 将文件名保存下来
        animation.cover = new_cover_name
        animation.save()
        # 将文件名扩散到所有的缓存
        utils.spread_cache_field(animation.id, animation.relations,
                                 lambda id_list: app_models.Animation.objects.filter(id__in=id_list).all(),
                                 'cover', new_cover_name)
        # 存储路径不存在时先创建路径
        if not os.path.exists(COVER_DIRS):
            os.makedirs(COVER_DIRS)
        # 该文件万一已经存在，就删除文件
        if os.path.exists(new_path):
            os.remove(new_path)
        # 将图像写入到一个临时的文件
        temp_path = '%s/temp-animation-%s.%s' % (COVER_DIRS, uuid.uuid4(), ext)
        with open(temp_path, 'wb') as f:
            for c in file.chunks():
                f.write(c)
        # 处理这张图片，对其进行裁切和缩放
        Cover.__analyse_image(temp_path, new_path)
        return HttpResponse(status=201)

    @staticmethod
    def __options():
        return HttpResponse(json.dumps({
            'name': 'Cover',
            'description': '',
            'renders': ["application/json", "text/html"],
            'parses': ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"],
            'actions': {
                'POST': {
                    'cover': {
                        'type': 'file',
                        'required': True,
                        'label': 'Cover'
                    }
                }
            }
        }), content_type='application/json')

    @staticmethod
    def __split_filename(filename):
        p = filename.rfind('.')
        if p >= 0:
            return filename[:p], filename[p + 1:]
        else:
            return filename, ''

    @staticmethod
    def __analyse_image(in_path, out_path, size=384):
        img = Image.open(in_path)
        # 裁剪成正方形
        width, height = img.size
        if width > height:
            img = img.crop(((width - height) / 2, 0, (width + height) / 2, height))
        elif width < height:
            img = img.crop((0, (height - width) / 2, width, (height + width) / 2))
        # 压缩到极小的尺寸
        img.thumbnail((size, size))
        img.save(out_path)
        os.remove(in_path)


class Profile:
    class Info(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = app_models.Profile.objects.all()
        serializer_class = app_serializers.Profile.Info
        permission_classes = (app_permissions.SelfOnly,)
        lookup_field = 'username'

        def list(self, request, *args, **kwargs):
            profile = request.user.profile
            return redirect('api-profile-info-detail', username=profile.username)

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

        def get_queryset(self):
            profile = self.request.user.profile
            queryset = self.queryset.filter(owner=profile).order_by('-create_time')
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
        search_fields = ('title', 'origin_title', 'other_title', 'tags__name', 'keyword')
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
                published_quantity = serializer.instance.published_quantity

                for diary in diaries:
                    diary.sum_quantity = sum_quantity
                    diary.published_quantity = published_quantity
                    if diary.status != enums.DiaryStatus.give_up:
                        if sum_quantity is None or published_quantity is None:
                            diary.status = enums.DiaryStatus.ready
                        elif diary.watched_quantity >= sum_quantity:
                            diary.status = enums.DiaryStatus.complete
                        else:
                            diary.status = enums.DiaryStatus.watching
                    diary.save()

    class Staff(viewsets.ModelViewSet):
        queryset = app_models.Staff.objects
        serializer_class = app_serializers.Database.Staff
        permission_classes = (app_permissions.IsStaffOrReadOnly,)
        lookup_field = 'id'
        filter_fields = ('is_organization',)
        search_fields = ('name', 'origin_name')
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
        filter_fields = ('title', 'status', 'watch_many_times', 'watch_original_work')
        search_fields = ('title',)
        ordering_fields = ('id', 'title', 'watched_quantity', 'sum_quantity', 'published_quantity', 'status',
                           'create_time', 'update_time')

        def get_queryset(self):
            return self.queryset.filter(owner=self.request.user.profile).all()

    class Comment(viewsets.ModelViewSet):
        queryset = app_models.Comment.objects
        serializer_class = app_serializers.Personal.Comment
        permission_classes = (app_permissions.SelfOnly,)
        lookup_field = 'animation_id'
        filter_fields = ('title', 'score')
        search_fields = ('title', 'short_comment', 'article')
        ordering_fields = ('id', 'title', 'score', 'create_time', 'update_time')

        def get_queryset(self):
            return self.queryset.filter(owner=self.request.user.profile).all()


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
        search_fields = ('username', 'name')
        ordering_fields = ('create_path', 'create_time', 'last_login')

    class Password(mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = app_models.Profile.objects
        serializer_class = app_serializers.Admin.Password
        permission_classes = (app_permissions.Password,)
        lookup_field = 'username'

    class RegistrationCode(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
        queryset = app_models.RegistrationCode.objects
        serializer_class = app_serializers.Admin.RegistrationCode
        permission_classes = (app_permissions.IsStaff,)
        lookup_field = 'id'
        filter_fields = ('enable',)
        ordering_fields = ('deadline', 'enable', 'used_time')

    class SystemMessage(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
        queryset = app_models.Message.objects.filter(type=enums.MessageType.system).order_by('-create_time')
        serializer_class = app_serializers.Admin.SystemMessage
        permission_classes = (app_permissions.IsStaff,)
        lookup_field = 'id'
        filter_fields = ('read', 'owner')
        ordering_fields = ('read', 'owner', 'create_time')
