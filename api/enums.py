PROFILE_CREATE_PATH_CHOICE = (
    ('REGISTER', 'Register'),
    ('ACTIVATE', 'Activate'),
    ('ADMIN', 'Administrator'),
    ('SYS', 'System')
)

MESSAGE_TYPE_CHOICE = (
    ('SYS', 'System'),
    ('CHAT', 'Chat'),
    ('UPDATE', 'Update')
)

ANIMATION_ORI_WORK_TYPE_CHOICE = (
    ('NOVEL', 'Novel'),
    ('MANGA', "Manga"),
    ('GAME', 'Game'),
    ('ORI', 'Original'),
    ('OTHER', 'Other')
)

ANIMATION_PUBLISH_TYPE_CHOICE = (
    ('GENERAL', 'TV & WEB'),
    ('MOVIE', 'MOVIE'),
    ('OVA', 'OVA & OAD')
)

ANIMATION_LIMIT_LEVEL_CHOICE = (
    ('ALL', 'ALL'),
    ('R12', 'R12'),
    ('R15', 'R15'),
    ('R17', 'R17'),
    ('R18', 'R18'),
    ('R18G', 'R18G')
)

DIARY_STATUS_CHOICE = (
    ('READY', 'Ready'),
    ('WATCHING', 'Watching'),
    ('COMPLETE', 'Complete'),
    ('GIVEUP', 'GiveUp')
)

GLOBAL_SETTING_REGISTER_MODE_CHOICE = (
    ('CLOSE', 'Close'),
    ('ONLY_CODE', 'OnlyCode'),
    ('OPEN', 'Open')
)


class ProfileCreatePath:
    register = 'REGISTER'
    activate = 'ACTIVATE'
    admin = 'ADMIN'
    system = 'SYS'


class MessageType:
    system = 'SYS'
    chat = 'CHAT'
    update = 'UPDATE'


class AnimationPublishType:
    general = 'GENERAL'
    movie = 'MOVIE'
    ova = 'OVA'


class DiaryStatus:
    ready = 'READY'
    watching = 'WATCHING'
    complete = 'COMPLETE'
    give_up = 'GIVEUP'


class GlobalSettingRegisterMode:
    close = 'CLOSE'
    only_code = 'ONLY_CODE'
    open = 'OPEN'
