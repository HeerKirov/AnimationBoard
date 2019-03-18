from django.urls import path
from rest_framework import routers
from . import views as app_views

router = routers.DefaultRouter()

router.register('user/login', app_views.User.Login, base_name='api-user-login')
router.register('user/token', app_views.User.Token, base_name='api-user-token')
router.register('user/logout', app_views.User.Logout, base_name='api-user-logout')
router.register('user/register', app_views.User.Register, base_name='api-user-register')

router.register('profile/info', app_views.Profile.Info, base_name='api-profile-info')
router.register('profile/password', app_views.Profile.Password, base_name='api-profile-password')
router.register('profile/messages', app_views.Profile.Message, base_name='api-profile-message')

router.register('database/animations', app_views.Database.Animation, base_name='api-database-animation')
router.register('database/staffs', app_views.Database.Staff, base_name='api-database-staff')
router.register('database/tags', app_views.Database.Tag, base_name='api-database-tag')

router.register('personal/diaries', app_views.Personal.Diary, base_name='api-personal-diary')
router.register('personal/comments', app_views.Personal.Comment, base_name='api-personal-comment')

router.register('admin/setting', app_views.Admin.Setting, base_name='api-admin-setting')
router.register('admin/users', app_views.Admin.User, base_name='api-admin-user')
router.register('admin/users-password', app_views.Admin.Password, base_name='api-admin-password')
router.register('admin/registration-code', app_views.Admin.RegistrationCode, base_name='api-admin-registration-code')
router.register('admin/system-messages', app_views.Admin.SystemMessage, base_name='api-admin-system-message')

urlpatterns = []
urlpatterns += router.urls
urlpatterns += [
    path('cover/<str:target>/<str:index>/', app_views.Cover.cover)
]