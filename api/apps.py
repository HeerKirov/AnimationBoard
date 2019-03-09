from django.apps import AppConfig
from django.db.models.signals import post_migrate


def check_initial_user():
    from . import enums, models as app_models, services
    import config
    print('Checking initial user... ', end='')
    if config.INITIAL_ADMIN_USER is None:
        print('Skipped')
    elif app_models.User.objects.filter(username=config.INITIAL_ADMIN_USER['username']).exists():
        print('Done')
    else:
        print('Not exist. Creating initial user...')
        services.Profile.create_full_user(username=config.INITIAL_ADMIN_USER['username'],
                                          name=config.INITIAL_ADMIN_USER['name'],
                                          password=config.INITIAL_ADMIN_USER['password'],
                                          is_staff=True, is_superuser=True,
                                          create_path=enums.ProfileCreatePath.system)
        print('Done.')


def check_initial_setting():
    from . import services
    import config
    print('Checking initial setting... ', end='')
    if config.INITIAL_SETTING is None:
        print('Skipped')
    elif services.Setting.exists():
        print('Done')
    else:
        print('Not exist. Creating initial setting...')
        services.Setting.create_setting(**config.INITIAL_SETTING)
        print('Done.')


def callback(sender, **kwargs):
    check_initial_user()
    check_initial_setting()


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        post_migrate.connect(callback, sender=self)
