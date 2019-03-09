URL_PREFIX = 'animation-board/'

DEBUG = True
SECRET_KEY = '@==@qtlw__ennaho9kq!l2z(1ox&a+b$ocmk+d07ay!60-%6by'

DATABASE = {
    'DATABASE': 'animation_board',
    'USERNAME': 'postgres',
    'PASSWORD': '',
    'HOST': 'localhost',
    'PORT': '5432'
}

INITIAL_ADMIN_USER = {
    'username': 'admin',
    'password': 'admin',
    'name': 'Administrator'
}

INITIAL_SETTING = {
    'register_mode': 'OPEN'
}

AUTO_UPDATE_SETTINGS = {
    'enable': True,
    'interval': '*/15 * * * *'
}
