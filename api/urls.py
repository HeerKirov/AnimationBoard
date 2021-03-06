from rest_framework import routers
from . import views as app_views

router = routers.DefaultRouter()

router.register('user/login', app_views.User.Login, base_name='api-user-login')
router.register('user/log-status', app_views.User.LogStatus, base_name='api-user-log-status')
router.register('user/token', app_views.User.Token, base_name='api-user-token')
router.register('user/refresh-token', app_views.User.RefreshToken, base_name='api-user-refresh-token')
router.register('user/logout', app_views.User.Logout, base_name='api-user-logout')
router.register('user/register', app_views.User.Register, base_name='api-user-register')

router.register('cover/animation', app_views.Cover.Animation, base_name='api-cover-animation')
router.register('cover/profile', app_views.Cover.Profile, base_name='api-cover-profile')
router.register('cover', app_views.Cover, base_name='api-cover')

router.register('profile/info', app_views.Profile.Info, base_name='api-profile-info')
router.register('profile/password', app_views.Profile.Password, base_name='api-profile-password')
router.register('profile/messages', app_views.Profile.Message, base_name='api-profile-message')

router.register('database/animations', app_views.Database.Animation, base_name='api-database-animation')
router.register('database/staffs', app_views.Database.Staff, base_name='api-database-staff')
router.register('database/tags', app_views.Database.Tag, base_name='api-database-tag')

router.register('personal/diaries', app_views.Personal.Diary, base_name='api-personal-diary')
router.register('personal/comments', app_views.Personal.Comment, base_name='api-personal-comment')

router.register('statistics', app_views.Statistics, base_name='api-statistics')

router.register('admin/setting', app_views.Admin.Setting, base_name='api-admin-setting')
router.register('admin/users', app_views.Admin.User, base_name='api-admin-user')
router.register('admin/users-permission', app_views.Admin.Permission, base_name='api-admin-permission')
router.register('admin/registration-code', app_views.Admin.RegistrationCode, base_name='api-admin-registration-code')
router.register('admin/system-messages', app_views.Admin.SystemMessage, base_name='api-admin-system-message')

urlpatterns = []
urlpatterns += router.urls
