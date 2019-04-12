from rest_framework import serializers, validators
from . import models as app_models, enums, relations as app_relations, services, exceptions as app_exceptions
from django.utils import timezone


class Util:
    class StaffInfo(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        name = serializers.CharField(allow_null=False, max_length=64)
        is_organization = serializers.BooleanField(allow_null=False)

        class Meta:
            model = app_models.Staff
            fields = ('id', 'name', 'is_organization')


class User:
    class Login(serializers.Serializer):
        username = serializers.CharField(max_length=150, allow_null=False, allow_blank=False, write_only=True)
        password = serializers.CharField(max_length=256, allow_null=False, allow_blank=False, write_only=True)

        class Meta:
            fields = ('username', 'password')

    class Token(serializers.Serializer):
        username = serializers.CharField(max_length=150, allow_null=False, allow_blank=False, write_only=True)
        password = serializers.CharField(max_length=256, allow_null=False, allow_blank=False, write_only=True)

        class Meta:
            fields = ('username', 'password')

    class Register(serializers.Serializer):
        username = serializers.CharField(max_length=150, allow_null=False, allow_blank=False, write_only=True)
        name = serializers.CharField(max_length=32, allow_null=False, allow_blank=False, write_only=True)
        password = serializers.CharField(max_length=256, allow_null=False, allow_blank=False, write_only=True)

        registration_code = serializers.CharField(max_length=256, allow_null=True, allow_blank=True, write_only=True)

        class Meta:
            fields = ('username', 'password', 'name', 'registration_code')


class Profile:
    class Info(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        cover = serializers.CharField(read_only=True)
        username = serializers.CharField(read_only=True)
        name = serializers.CharField(max_length=32, allow_null=False, allow_blank=False)
        create_time = serializers.DateTimeField(read_only=True)

        last_login = serializers.DateTimeField(read_only=True)
        last_ip = serializers.CharField(read_only=True)

        is_staff = serializers.BooleanField(read_only=True, source='user.is_staff')
        is_superuser = serializers.BooleanField(read_only=True, source='user.is_superuser')

        animation_update_notice = serializers.BooleanField(allow_null=False, required=False)
        night_update_mode = serializers.BooleanField(allow_null=False, required=False)

        class Meta:
            model = app_models.Profile
            fields = ('id', 'cover', 'username', 'name', 'create_time', 'last_login', 'last_ip',
                      'is_staff', 'is_superuser',
                      'animation_update_notice', 'night_update_mode')

    class Password(serializers.Serializer):
        old_password = serializers.CharField(write_only=True, allow_null=False, allow_blank=False,
                                             style={'input_type': 'password'})
        new_password = serializers.CharField(write_only=True, allow_null=False, allow_blank=False,
                                             style={'input_type': 'password'})

        class Meta:
            fields = ('old_password', 'new_password')

    class Message(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)

        read = serializers.BooleanField(allow_null=False, default=False)
        type = serializers.ChoiceField(choices=enums.MESSAGE_TYPE_CHOICE, read_only=True)
        content = serializers.JSONField(read_only=True)

        create_time = serializers.DateTimeField(allow_null=False, read_only=True)
        sender = serializers.SlugRelatedField(read_only=True, slug_field='username')
        sender_name = serializers.SlugRelatedField(read_only=True, slug_field='name', source='sender')

        def create(self, validated_data):
            profile = self.context['request'].user.profile
            validated_data['owner'] = profile
            return super().create(validated_data)

        class Meta:
            model = app_models.Message
            fields = ('id', 'read', 'type', 'content', 'create_time', 'sender', 'sender_name')


class Database:
    class Animation(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        cover = serializers.CharField(read_only=True)
        title = serializers.CharField(allow_null=False, allow_blank=False, max_length=64)
        origin_title = serializers.CharField(allow_null=True, max_length=64)
        other_title = serializers.CharField(allow_null=True, max_length=64)

        original_work_type = serializers.ChoiceField(enums.ANIMATION_ORI_WORK_TYPE_CHOICE, allow_null=True, default=None)
        original_work_authors = serializers.PrimaryKeyRelatedField(queryset=app_models.Staff.objects.all(), many=True)
        staff_companies = serializers.PrimaryKeyRelatedField(queryset=app_models.Staff.objects.all(), many=True)
        staff_supervisors = serializers.PrimaryKeyRelatedField(queryset=app_models.Staff.objects.all(), many=True)

        staff_info = Util.StaffInfo(read_only=True, many=True, source='all_staffs')

        publish_type = serializers.ChoiceField(enums.ANIMATION_PUBLISH_TYPE_CHOICE, allow_null=False)
        publish_time = serializers.DateField(allow_null=True)
        sum_quantity = serializers.IntegerField(allow_null=True, min_value=0)
        published_quantity = serializers.IntegerField(allow_null=True, min_value=0)
        duration = serializers.IntegerField(allow_null=True)
        publish_plan = serializers.ListField(child=serializers.DateTimeField(allow_null=False), allow_null=False,
                                             default=lambda: [])
        published_record = serializers.ListField(child=serializers.DateTimeField(allow_null=False), read_only=True)
        subtitle_list = serializers.ListField(child=serializers.CharField(max_length=64, allow_null=False),
                                              allow_null=False, default=lambda: [])

        introduction = serializers.CharField(allow_null=True)
        keyword = serializers.CharField(allow_null=True)
        links = serializers.ListField(child=serializers.CharField(allow_null=False), allow_null=False,
                                      default=lambda: [])
        tags = serializers.SlugRelatedField(slug_field='name', many=True, queryset=app_models.Tag.objects.all())
        limit_level = serializers.ChoiceField(enums.ANIMATION_LIMIT_LEVEL_CHOICE, allow_null=True)

        relations = serializers.JSONField(read_only=True)
        original_relations = serializers.JSONField(allow_null=False, required=False, default=lambda: {})

        create_time = serializers.DateTimeField(read_only=True)
        creator = serializers.CharField(read_only=True)
        update_time = serializers.DateTimeField(read_only=True)
        updater = serializers.CharField(read_only=True)

        def __init__(self, *args, **kwargs):
            simple = kwargs.pop('simple', False)
            super(Database.Animation, self).__init__(*args, **kwargs)
            if simple:
                exclude = ['original_relations', 'links', 'relations', 'subtitle_list', 'published_record']
                for field_name in exclude:
                    self.fields.pop(field_name)

        def __new__(cls, *args, **kwargs):
            many = kwargs.get('many', False)
            if many:
                kwargs['simple'] = True
            return super(Database.Animation, cls).__new__(cls, *args, **kwargs)

        def create(self, validated_data):
            validated_data['published_record'] = []
            sum_quantity = validated_data.get('sum_quantity')
            published_quantity = validated_data.get('published_quantity')
            if sum_quantity is None:
                published_quantity = None
            elif published_quantity is not None and published_quantity > sum_quantity:
                published_quantity = sum_quantity
            validated_data['sum_quantity'] = sum_quantity
            validated_data['published_quantity'] = published_quantity

            if 'original_relations' in validated_data and validated_data['original_relations'] is not None:
                original_relations = validated_data.pop('original_relations')
                self.check_original_relations(original_relations)
                validated_data['relations'] = {}
                validated_data['original_relations'] = {}
                instance = super().create(validated_data)
                app_relations.RelationsMap(lambda i: app_models.Animation.objects.filter(id=i).first() if i >= 0 else instance,
                                           -1, original_relations)
                return app_models.Animation.objects.filter(id=instance.id).first()
            else:
                validated_data['relations'] = {}
                validated_data['original_relations'] = {}
                return super().create(validated_data)

        def update(self, instance, validated_data):
            if 'sum_quantity' in validated_data or 'published_quantity' in validated_data:
                sum_quantity = validated_data['sum_quantity'] if 'sum_quantity' in validated_data else instance.sum_quantity
                published_quantity = validated_data['published_quantity'] if 'published_quantity' in validated_data \
                    else instance.published_quantity

                if sum_quantity is None:
                    published_quantity = None
                elif published_quantity is not None and published_quantity > sum_quantity:
                    published_quantity = sum_quantity
                validated_data['sum_quantity'] = sum_quantity
                validated_data['published_quantity'] = published_quantity

            if 'original_relations' in validated_data and validated_data['original_relations'] is not None:
                original_relations = validated_data.pop('original_relations')
                self.check_original_relations(original_relations)
                super().update(instance, validated_data)    # 对animation主体的保存早于拓扑
                app_relations.RelationsMap(lambda i: app_models.Animation.objects.filter(id=i).first(),
                                       instance.id, original_relations)
                return app_models.Animation.objects.filter(id=instance.id).first()
            else:
                # 在没有更新关系，且更新了title时，才会把title更新到拓扑。
                if 'title' in validated_data:
                    app_relations.spread_cache_field(instance.id, instance.relations,
                                                 lambda id_list: app_models.Animation.objects.filter(id__in=id_list).all(),
                                             'title', validated_data.get('title'))
                return super().update(instance, validated_data)

        @staticmethod
        def check_original_relations(relations):
            if relations is None:
                raise app_exceptions.ApiError('RelationError', 'Relations cannot be null.')
            id_set = set()
            for (rel, id_list) in relations.items():
                if rel not in app_relations.RELATIONS:
                    raise app_exceptions.ApiError('RelationError', 'Relations cannot be "%s".' % (rel,))
                if not isinstance(id_list, list):
                    raise app_exceptions.ApiError('RelationError', 'Relation value must be list.')
                for i in id_list:
                    if not isinstance(i, int):
                        raise app_exceptions.ApiError('RelationError', 'Relation value item must be int.')
                    if i in id_set:
                        raise app_exceptions.ApiError('RelationError', 'Animation id "%s" is repeated.' % (i,))
                    id_set.add(i)

        class Meta:
            model = app_models.Animation
            fields = ('id', 'cover', 'title', 'origin_title', 'other_title', 'staff_info',
                      'original_work_type', 'original_work_authors', 'staff_companies', 'staff_supervisors',
                      'publish_type', 'publish_time', 'sum_quantity', 'published_quantity',
                      'duration', 'publish_plan', 'subtitle_list', 'published_record',
                      'introduction', 'keyword', 'links', 'tags', 'limit_level', 'relations', 'original_relations',
                      'create_time', 'creator', 'update_time', 'updater')

    class Staff(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        name = serializers.CharField(allow_null=False, max_length=64)
        origin_name = serializers.CharField(allow_null=True, max_length=64)
        remark = serializers.CharField(allow_null=True, max_length=64)
        is_organization = serializers.BooleanField(allow_null=False)

        create_time = serializers.DateTimeField(read_only=True)
        creator = serializers.CharField(read_only=True)
        update_time = serializers.DateTimeField(read_only=True)
        updater = serializers.CharField(read_only=True)

        class Meta:
            model = app_models.Staff
            fields = ('id', 'name', 'origin_name', 'remark', 'is_organization',
                      'create_time', 'creator', 'update_time', 'updater')

    class Tag(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        name = serializers.CharField(allow_null=False, max_length=16,
                                     validators=[validators.UniqueValidator(queryset=app_models.Tag.objects.all())])
        introduction = serializers.CharField(allow_null=True)

        create_time = serializers.DateTimeField(read_only=True)
        creator = serializers.CharField(read_only=True)
        update_time = serializers.DateTimeField(read_only=True)
        updater = serializers.CharField(read_only=True)

        class Meta:
            model = app_models.Tag
            fields = ('id', 'name', 'introduction',
                      'create_time', 'creator', 'update_time', 'updater')


class Statistics(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    type = serializers.CharField(read_only=True)
    key = serializers.CharField(read_only=True)
    content = serializers.JSONField(read_only=True)

    create_time = serializers.DateTimeField(read_only=True)
    update_time = serializers.DateTimeField(read_only=True)

    class Meta:
        model = app_models.Statistics
        fields = ('id', 'type', 'key', 'content', 'create_time', 'update_time')


class Personal:
    class Diary(serializers.ModelSerializer):
        supplement = serializers.BooleanField(write_only=True, default=False)
        id = serializers.IntegerField(read_only=True)
        title = serializers.CharField(read_only=True, source='animation.title')
        cover = serializers.CharField(read_only=True, source='animation.cover')
        animation = serializers.PrimaryKeyRelatedField(queryset=app_models.Animation.objects.all(), allow_null=False)

        watched_record = serializers.ListField(child=serializers.DateTimeField(), read_only=True)
        publish_plan = serializers.ListField(child=serializers.DateTimeField(allow_null=False), read_only=True,
                                             source='animation.publish_plan')
        watched_quantity = serializers.IntegerField(allow_null=False, min_value=0, required=False)
        sum_quantity = serializers.IntegerField(read_only=True, source='animation.sum_quantity')
        published_quantity = serializers.IntegerField(read_only=True, source='animation.published_quantity')
        status = serializers.ChoiceField(enums.DIARY_STATUS_CHOICE, required=False, allow_null=False)
        subscription_time = serializers.DateTimeField(allow_null=True, default=None)
        finish_time = serializers.DateTimeField(allow_null=True, default=None)

        watch_many_times = serializers.BooleanField(allow_null=False, default=False)
        watch_original_work = serializers.BooleanField(allow_null=False, default=False)

        create_time = serializers.DateTimeField(read_only=True)
        update_time = serializers.DateTimeField(read_only=True)

        def __init__(self, *args, **kwargs):
            simple = kwargs.pop('simple', False)
            super(Personal.Diary, self).__init__(*args, **kwargs)
            if simple:
                exclude = ['watched_record']
                for field_name in exclude:
                    self.fields.pop(field_name)

        def __new__(cls, *args, **kwargs):
            many = kwargs.get('many', False)
            if many:
                kwargs['simple'] = True
            return super(Personal.Diary, cls).__new__(cls, *args, **kwargs)

        def create(self, validated_data):
            """
            创建一个新的diary条目。
            创建条目的核心输入模型：
            1： 全新的订阅模型。它将全面纳入新系统的框架管理，有完整的订阅 - 看完周期，观看记录和观看数量。
                使用该模型不允许自定义watched quantity数量（就算有也是和update一样的逻辑），默认为0；
                使用该模型自动将subscription time设定为create time，不允许变更；
                使用该模型自动在watched不小于sum时设定finish time，不允许手动修改。
            2： 补充记录模型。它意在补充那些在之前就看完或早就开始看了的记录。这将允许订阅时间|观看记录出现缺口，并允许手动填写订阅时间|看完时间。
                watched quantity将手动填写。已完结番剧填写为sum的值，
                                            将录入一个已结束的旧记录，会将record设为空list，
                                            否则会填写为一个填满null的list（表示过去的观看记录丢失）。默认该值为None，视作sum。
                subscription time默认为null，但可以手动填写。
                finish time，如果watched >= sum，那么必须手动填写一个值，否则无视该值填写为null。finish的值不能早于subscription的值。
                补充模型自由度看起来更高，但缺失部分关键信息会导致统计空缺。
            此外，这个模型仅限create。在create之后，爱怎么折腾怎么折腾，行为都是一致的。
            也就是说，补充记录模型必须在create时一次填好，不然就删了重写。
            补充记录模型在animation有sum和至少1个publish之前禁止使用。都没发布补个鬼。
            :param validated_data:
            :return:
            """
            profile = self.context['request'].user.profile
            animation = validated_data['animation']
            if app_models.Diary.objects.filter(animation=animation, owner=profile).exists():
                raise app_exceptions.ApiError('Exists', 'Diary of this animation is exists.')
            validated_data['owner'] = profile
            if validated_data.get('supplement'):
                if animation.sum_quantity is None \
                        or animation.published_quantity is None or animation.published_quantity <= 0:
                    raise app_exceptions.ApiError('SupplementForbidden',
                                                  'Supplement mode cannot be used before animation is published.')
                return self.create_supplement({
                    'owner': profile,
                    'animation': animation,
                    'status': validated_data.get('status', None),
                    'watched_quantity': validated_data.get('watched_quantity', animation.sum_quantity),
                    'subscription_time': validated_data.get('subscription_time', None),
                    'finish_time': validated_data.get('finish_time', None),
                    'watch_many_times': validated_data.get('watch_many_times'),
                    'watch_original_work': validated_data.get('watch_original_work')
                })
            else:
                return self.create_subscription({
                    'owner': profile,
                    'animation': animation,
                    'status': validated_data.get('status', None),
                    'watched_quantity': validated_data.get('watched_quantity', 0),
                    'subscription_time': timezone.now(),
                    'watch_many_times': validated_data.get('watch_many_times'),
                    'watch_original_work': validated_data.get('watch_original_work')
                })

        def create_supplement(self, validated_data):
            animation = validated_data['animation']
            if animation.sum_quantity is not None and animation.published_quantity is not None:
                sum_quantity = animation.sum_quantity
                published_quantity = animation.published_quantity or 0
            else:
                sum_quantity = None
                published_quantity = 0

            # 约束watched_quantity和watched_record的数量不超过published_quantity.
            if validated_data['watched_quantity'] > published_quantity:
                validated_data['watched_quantity'] = published_quantity
            watched_quantity = validated_data['watched_quantity']

            status = validated_data.pop('status', None) or enums.DiaryStatus.watching
            finish_time = validated_data.pop('finish_time')
            subscription_time = validated_data.get('subscription_time')
            if status != enums.DiaryStatus.give_up:
                if sum_quantity is not None:
                    if watched_quantity >= sum_quantity:
                        validated_data['status'] = enums.DiaryStatus.complete
                        if finish_time is None:
                            raise app_exceptions.ApiError('FinishTimeNeed',
                                                          '"finish_time" is needed in supplement mode.')
                        elif subscription_time is not None and finish_time < subscription_time:
                            raise app_exceptions.ApiError('FinishTimeInvalid',
                                                          'finish_time must be lessa than subscription_time.')
                        validated_data['finish_time'] = finish_time
                    else:
                        validated_data['status'] = enums.DiaryStatus.watching
                else:
                    validated_data['status'] = enums.DiaryStatus.ready
            else:
                validated_data['status'] = enums.DiaryStatus.give_up

            if 0 < watched_quantity < sum_quantity:
                validated_data['watched_record'] = [None for _ in range(0, watched_quantity)]
            else:
                validated_data['watched_record'] = []

            return super().create(validated_data)

        def create_subscription(self, validated_data):
            animation = validated_data['animation']
            if animation.sum_quantity is not None and animation.published_quantity is not None:
                # 提取出一个能用于约束下级数值的sum_quantity。没有时是None，因为只是个标杆。
                sum_quantity = animation.sum_quantity
                # 提取出一个能用于约束下级数值的published_quantity。没有时识别为0，因为要直接用这个数值限制watched.
                published_quantity = animation.published_quantity or 0
            else:
                sum_quantity = None
                published_quantity = 0

            # 约束watched_quantity和watched_record的数量不超过published_quantity.
            if validated_data['watched_quantity'] > published_quantity:
                validated_data['watched_quantity'] = published_quantity
            watched_quantity = validated_data.get('watched_quantity')

            status = validated_data.pop('status', enums.DiaryStatus.watching)
            if status != enums.DiaryStatus.give_up:
                if sum_quantity is not None:
                    if watched_quantity >= sum_quantity:
                        validated_data['finish_time'] = timezone.now()
                        validated_data['status'] = enums.DiaryStatus.complete
                    else:
                        validated_data['status'] = enums.DiaryStatus.watching
                else:
                    validated_data['status'] = enums.DiaryStatus.ready
            else:
                validated_data['status'] = enums.DiaryStatus.give_up

            if watched_quantity > 0:
                now = timezone.now()
                validated_data['watched_record'] = [now for _ in range(0, watched_quantity)]
            else:
                validated_data['watched_record'] = []

            return super().create(validated_data)

        def update(self, instance, validated_data):
            if 'animation' in validated_data:
                del validated_data['animation']
            if 'subscription_time' in validated_data:
                del validated_data['subscription_time']
            if 'finish_time' in validated_data:
                del validated_data['finish_time']
            if 'mode' in validated_data:
                del validated_data['mode']
            # 提取出latest的sum_quantity。
            sum_quantity = instance.animation.sum_quantity
            # 提取出latest的published_quantity。
            published_quantity = instance.animation.published_quantity or 0

            # 约束watched_quantity和watched_record的数量不超过published_quantity.
            if validated_data.get('watched_quantity') is not None \
                    and validated_data['watched_quantity'] > published_quantity:
                validated_data['watched_quantity'] = published_quantity
            watched_quantity = validated_data.get('watched_quantity', None)
            if watched_quantity is None:
                watched_quantity = instance.watched_quantity

            status = validated_data.pop('status', None) or instance.status
            if status != enums.DiaryStatus.give_up:
                if sum_quantity is not None:
                    if watched_quantity >= sum_quantity:
                        validated_data['status'] = enums.DiaryStatus.complete
                        if instance.finish_time is None:
                            validated_data['finish_time'] = timezone.now()
                    else:
                        validated_data['status'] = enums.DiaryStatus.watching
                else:
                    validated_data['status'] = enums.DiaryStatus.ready
            else:
                validated_data['status'] = enums.DiaryStatus.give_up

            if watched_quantity > len(instance.watched_record):
                now = timezone.now()
                r = range(len(instance.watched_record), watched_quantity)
                validated_data['watched_record'] = instance.watched_record + [now for _ in r]
            elif watched_quantity < len(instance.watched_record):
                validated_data['watched_record'] = instance.watched_record[:watched_quantity]

            return super().update(instance, validated_data)

        class Meta:
            model = app_models.Diary
            fields = ('id', 'title', 'cover', 'animation', 'watched_record', 'publish_plan', 'supplement',
                      'watched_quantity', 'sum_quantity', 'published_quantity', 'finish_time', 'subscription_time',
                      'status', 'watch_many_times', 'watch_original_work', 'create_time', 'update_time')

    class Comment(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        title = serializers.CharField(read_only=True, source='animation.title')
        cover = serializers.CharField(read_only=True, source='animation.cover')
        animation = serializers.PrimaryKeyRelatedField(queryset=app_models.Animation.objects.all(), allow_null=False)

        score = serializers.IntegerField(allow_null=True, default=None, min_value=1, max_value=10)
        short_comment = serializers.CharField(max_length=128, allow_null=True, default=None)
        article = serializers.CharField(allow_null=True, default=None)

        create_time = serializers.DateTimeField(read_only=True)
        update_time = serializers.DateTimeField(read_only=True)

        def create(self, validated_data):
            profile = self.context['request'].user.profile
            animation = validated_data['animation']
            if animation is not None:
                if app_models.Comment.objects.filter(animation=animation, owner=profile).exists():
                    raise app_exceptions.ApiError('Exists', 'Comment of this animation is exists.')
            validated_data['owner'] = profile
            return super().create(validated_data)

        def update(self, instance, validated_data):
            if 'animation' in validated_data:
                del validated_data['animation']
            return super().update(instance, validated_data)

        class Meta:
            model = app_models.Comment
            fields = ('id', 'title', 'cover', 'animation', 'score', 'short_comment', 'article',
                      'create_time', 'update_time')


class Admin:
    class Setting(serializers.ModelSerializer):
        register_mode = serializers.ChoiceField(enums.GLOBAL_SETTING_REGISTER_MODE_CHOICE, allow_null=False)

        class Meta:
            model = app_models.GlobalSetting
            fields = ('register_mode',)

    class User(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        username = serializers.CharField(read_only=True)
        name = serializers.CharField(max_length=32, allow_null=False)

        last_login_time = serializers.DateTimeField(read_only=True)
        last_login_ip = serializers.CharField(read_only=True)

        create_time = serializers.DateTimeField(read_only=True)
        create_path = serializers.CharField(read_only=True)

        is_staff = serializers.BooleanField(read_only=True, source='user.is_staff')
        is_superuser = serializers.BooleanField(read_only=True, source='user.is_superuser')

        class Meta:
            model = app_models.Profile
            fields = ('id', 'username', 'name', 'last_login_time', 'last_login_ip', 'create_time', 'create_path',
                      'is_staff', 'is_superuser')

    class Permission(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        username = serializers.CharField(read_only=True)
        name = serializers.CharField(read_only=True)
        password = serializers.CharField(write_only=True, required=False, allow_blank=False,
                                         style={'input_type': 'password'})
        is_staff = serializers.BooleanField(required=False, write_only=True)

        def update(self, instance, validated_data):
            user = instance.user
            if 'password' in validated_data:
                password = validated_data.pop('password')
                user.set_password(password)
            if 'is_staff' in validated_data:
                is_staff = validated_data.pop('is_staff')
                user.is_staff = is_staff
            user.save()
            return super().update(instance, validated_data)

        class Meta:
            model = app_models.Profile
            fields = ('id', 'username', 'name', 'password', 'is_staff')

    class RegistrationCode(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        code = serializers.CharField(read_only=True)
        enable = serializers.BooleanField(read_only=True)
        deadline = serializers.DateTimeField(allow_null=True, default=None)

        used_time = serializers.DateTimeField(read_only=True)
        create_time = serializers.DateTimeField(read_only=True)
        used_user = serializers.CharField(read_only=True)

        def create(self, validated_data):
            validated_data['code'] = services.RegistrationCode.generate_code()
            return super().create(validated_data)

        class Meta:
            model = app_models.RegistrationCode
            fields = ('id', 'code', 'enable', 'deadline', 'used_time', 'create_time', 'used_user')

    class SystemMessage(serializers.ModelSerializer):
        id = serializers.IntegerField(read_only=True)
        owner = serializers.SlugRelatedField(slug_field='username', queryset=app_models.Profile.objects.all())
        type = serializers.CharField(read_only=True)
        content = serializers.JSONField(read_only=True)
        system_message_content = serializers.CharField(write_only=True, allow_null=False)

        read = serializers.BooleanField(read_only=True)
        create_time = serializers.DateTimeField(read_only=True)

        def create(self, validated_data):
            validated_data['type'] = enums.MessageType.system
            validated_data['content'] = {'content': validated_data.pop('system_message_content')}
            return super().create(validated_data)

        class Meta:
            model = app_models.Message
            fields = ('id', 'owner', 'type', 'content', 'system_message_content', 'read', 'create_time')
