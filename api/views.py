from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import viewsets, response, status, exceptions, permissions, mixins
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from . import exceptions as app_exceptions, serializers as app_serializers
from . import permissions as app_permissions, models as app_models, enums, services


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
                    return response.Response({'detail': 'Register by registration key was forbidden by admin.'},
                                             status=status.HTTP_403_FORBIDDEN)
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
                    return response.Response({'detail': 'Register was forbidden by admin.'},
                                             status=status.HTTP_403_FORBIDDEN)
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
        filter_fields = ('have_cover', 'original_work_type', 'publish_type', 'publish_time', 'limit_level', 'tags__name')
        search_fields = ('title', 'origin_title', 'other_title', 'tags__name')
        ordering_fields = ('id', 'title', 'original_work_type', 'publish_type', 'limit_level', 'create_time', 'update_time')

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
        lookup_field = 'id'
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
        lookup_field = 'id'
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
        lookup_field = 'id'
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
