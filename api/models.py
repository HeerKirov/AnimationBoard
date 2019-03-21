from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField, ArrayField
from . import enums
from django.utils import timezone


class Profile(models.Model):
    id = models.AutoField(primary_key=True, null=False, blank=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=32)
    cover = models.CharField(max_length=256, null=True, default=None)

    animation_update_notice = models.BooleanField(null=False, default=True)     # 订阅的动画更新时，会发送消息提示
    night_update_mode = models.BooleanField(null=False, default=False)          # 使用深夜动画表(26:00模式)

    enable = models.BooleanField(null=False, default=True)
    create_path = models.CharField(max_length=8, null=False, blank=False, choices=enums.PROFILE_CREATE_PATH_CHOICE)
    create_time = models.DateTimeField(null=False, auto_now_add=True)
    last_login_time = models.DateTimeField(null=True, default=None)
    last_login_ip = models.TextField(null=True, default=None)

    username = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return "<[%s]%s>" % (self.username, self.name)


class Message(models.Model):
    """有关Message的说明
        Message的Type分为N种，详见enums。
        下面主要说明不同type的content的结构。
        1. System 系统通知类
        {
            "content": <string>
        }
        2. Chat 消息类
        {
            "content": <string>
        }
        3. Update 番剧更新通知
        {
            "update": [
                {
                    "animation_id": <int>,
                    "range_old": <int>,  # not included
                    "range_new": <int>,
                    "range_max": <int>,  # sum_quantity
                    "animation_title": <string>
                }
            ]
        } ]
        }
        """
    id = models.BigAutoField(primary_key=True, null=False)
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, null=False, related_name='messages_by_owner')
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, null=True, related_name='messages_by_sender')
    type = models.CharField(choices=enums.MESSAGE_TYPE_CHOICE, null=False, max_length=8)
    content = JSONField(null=False)
    read = models.BooleanField(null=False, default=False)
    create_time = models.DateTimeField(null=False, auto_now_add=True)


class RegistrationCode(models.Model):
    id = models.BigAutoField(primary_key=True, null=False)
    code = models.TextField(null=False)
    enable = models.BooleanField(null=False, default=True)
    deadline = models.DateTimeField(null=True, default=None)
    used_time = models.DateTimeField(null=True, default=None)
    create_time = models.DateTimeField(null=False, auto_now_add=True)
    used_user = models.CharField(max_length=150, null=True, default=None)


class Animation(models.Model):
    id = models.BigAutoField(primary_key=True, null=False)
    cover = models.CharField(max_length=256, null=True, default=None)
    title = models.CharField(max_length=64, null=False, blank=False)
    origin_title = models.CharField(max_length=64, null=True)
    other_title = models.CharField(max_length=64, null=True)

    original_work_type = models.CharField(max_length=6, choices=enums.ANIMATION_ORI_WORK_TYPE_CHOICE, null=True)
    original_work_authors = models.ManyToManyField('Staff', related_name='animations_by_authors')
    staff_companies = models.ManyToManyField('Staff', related_name='animations_by_companies')
    staff_supervisors = models.ManyToManyField('Staff', related_name='animations_by_supervisors')

    publish_type = models.CharField(choices=enums.ANIMATION_PUBLISH_TYPE_CHOICE, max_length=8, null=False)
    publish_time = models.DateField(null=True)
    sum_quantity = models.IntegerField(null=True)
    published_quantity = models.IntegerField(null=True)
    duration = models.IntegerField(null=True)
    publish_plan = ArrayField(models.DateTimeField(null=False), null=False)
    subtitle_list = ArrayField(models.CharField(max_length=64, null=False), null=False)

    introduction = models.TextField(null=True)
    keyword = models.TextField(null=True)
    links = ArrayField(models.TextField(null=False), null=False)
    tags = models.ManyToManyField('Tag', related_name='animations')
    limit_level = models.CharField(choices=enums.ANIMATION_LIMIT_LEVEL_CHOICE, max_length=6, null=True)

    relations = JSONField(null=False)
    original_relations = JSONField(null=False)

    create_time = models.DateTimeField(null=False, auto_now_add=True)
    creator = models.CharField(max_length=64, null=False)
    update_time = models.DateTimeField(null=True, auto_now=True)
    updater = models.CharField(max_length=64, null=True)

    def __str__(self):
        return "<[%s]%s>" % (self.id, self.title)

    @property
    def all_staffs(self):
        return self.original_work_authors.all() | self.staff_companies.all() | self.staff_supervisors.all()

    def take_published_count(self):
        now = timezone.now()
        ret_plan = []
        count = 0
        for i in self.publish_plan:
            if now >= i:
                count += 1
            else:
                ret_plan.append(i)
        return count, ret_plan


class Staff(models.Model):
    id = models.BigAutoField(primary_key=True, null=False)
    name = models.CharField(max_length=64, null=False)
    origin_name = models.CharField(max_length=64, null=True)
    is_organization = models.BooleanField(null=False)

    create_time = models.DateTimeField(null=False, auto_now_add=True)
    creator = models.CharField(max_length=64, null=False)
    update_time = models.DateTimeField(null=True, auto_now=True)
    updater = models.CharField(max_length=64, null=True)

    def __str__(self):
        return "<[%s]%s>" % (self.id, self.name)

    @property
    def simple_info(self):
        return {'id': self.id, 'name': self.name, 'is_organization': self.is_organization}


class Tag(models.Model):
    id = models.BigAutoField(primary_key=True, null=False)
    name = models.CharField(max_length=16, null=False, unique=True)
    introduction = models.TextField(null=True)

    create_time = models.DateTimeField(null=False, auto_now_add=True)
    creator = models.CharField(max_length=64, null=False)
    update_time = models.DateTimeField(null=True, auto_now=True)
    updater = models.CharField(max_length=64, null=True)

    def __str__(self):
        return "<[%s]%s>" % (self.id, self.name)

    @property
    def simple_info(self):
        return {'id': self.id, 'name': self.name, 'introduction': self.introduction}


class Diary(models.Model):
    id = models.BigAutoField(primary_key=True, null=False)
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, null=False, related_name='diaries')
    animation = models.ForeignKey(Animation, on_delete=models.CASCADE, null=False, related_name='diaries')

    watched_record = ArrayField(models.DateTimeField(null=False), null=False)
    watched_quantity = models.IntegerField(null=False)
    status = models.CharField(choices=enums.DIARY_STATUS_CHOICE, max_length=10, null=False)
    finish_time = models.DateTimeField(null=True, default=None)

    watch_many_times = models.BooleanField(null=False)
    watch_original_work = models.BooleanField(null=False)

    create_time = models.DateTimeField(null=False, auto_now_add=True)
    update_time = models.DateTimeField(null=True, auto_now=True)

    # TODO 由于publish plan字段强制使用了连接，这些缓存字段也可以用了，因此可以去掉了。
    title = models.CharField(max_length=64, null=False, blank=False)
    cover = models.CharField(max_length=256, null=True, default=None)
    sum_quantity = models.IntegerField(null=True)
    published_quantity = models.IntegerField(null=True)


class Comment(models.Model):
    id = models.BigAutoField(primary_key=True, null=False)
    owner = models.ForeignKey(Profile, on_delete=models.CASCADE, null=False, related_name='comments')
    animation = models.ForeignKey(Animation, on_delete=models.CASCADE, null=False, related_name='comments')

    score = models.IntegerField(null=True, default=None)
    short_comment = models.CharField(max_length=128, null=True, default=None)
    article = models.TextField(null=True, default=None)

    create_time = models.DateTimeField(null=False, auto_now_add=True)
    update_time = models.DateTimeField(null=True, auto_now=True)

    title = models.CharField(max_length=64, null=False, blank=False)


class GlobalSetting(models.Model):
    register_mode = models.CharField(choices=enums.GLOBAL_SETTING_REGISTER_MODE_CHOICE, max_length=10, null=False)
