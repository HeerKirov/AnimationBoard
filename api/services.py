from django.utils import timezone
from django.db.models import F, Q
from . import models as app_models, enums, statistics, exceptions as app_exceptions
import uuid


class Profile:
    @staticmethod
    def create_full_user(**kwargs):
        user = app_models.User(username=kwargs['username'])
        user.set_password(kwargs['password'])
        user.is_staff = kwargs['is_staff']
        user.is_superuser = kwargs['is_superuser']
        user.save()
        profile = app_models.Profile(user=user, username=kwargs['username'], name=kwargs['name'],
                                     create_path=kwargs['create_path'])
        profile.save()
        return profile


class Message:
    @staticmethod
    def send_system_notice(owner, content):
        msg = app_models.Message(type=enums.MessageType.system, content={"content": content}, owner=owner)
        msg.save()
        return msg

    @staticmethod
    def send_chat(owner, sender, content):
        msg = app_models.Message(type=enums.MessageType.chat, content={"content": content}, owner=owner, sender=sender)
        msg.save()
        return msg

    @staticmethod
    def send_delivery_update(owner, updates):
        profile = app_models.Profile.objects.filter(id__exact=owner.id).first()
        if profile.animation_update_notice:
            msg = app_models.Message(type=enums.MessageType.update, content={"update": updates}, owner=owner)
            msg.save()
            return msg
        return None


class RegistrationCode:
    @staticmethod
    def generate_code():
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(timezone.now().timestamp()))


class Animation:
    @staticmethod
    def refresh_published():
        print('Animation refresh published.')
        animations = app_models.Animation.objects.filter(Q(published_quantity__lt=F('sum_quantity')) |
                                                         Q(published_quantity__isnull=True),
                                                         sum_quantity__isnull=False).all()
        send_data = {}
        count = 0
        for animation in animations:
            if len(animation.publish_plan) > 0 and animation.sum_quantity is not None:
                published_count, new_plan, new_record = animation.take_published_count()
                if published_count > 0:
                    count += 1
                    if animation.published_quantity is None:
                        animation.published_quantity = 0
                    old_quantity = animation.published_quantity
                    if len(animation.published_record) < animation.published_quantity:
                        animation.published_record += \
                            [None for _ in range(0, animation.published_quantity - len(animation.published_record))]
                    elif len(animation.published_record) > animation.published_quantity:
                        animation.published_record = animation.published_record[:animation.published_quantity]

                    animation.publish_plan = new_plan
                    animation.published_quantity += published_count
                    animation.published_record += new_record
                    if animation.published_quantity > animation.sum_quantity:
                        animation.published_quantity = animation.sum_quantity
                    animation.save()

                    new_quantity = animation.published_quantity
                    if hasattr(animation, 'diaries'):
                        data = {
                            'animation_id': animation.id,
                            "animation_title": animation.title,
                            "range_old": old_quantity,
                            "range_new": new_quantity,
                            "range_max": animation.sum_quantity
                        }
                        now = timezone.now()
                        for diary in animation.diaries.all():
                            if diary.status == enums.DiaryStatus.ready:
                                diary.status = enums.DiaryStatus.watching
                                diary.save()
                            if diary.owner not in send_data:
                                updates = []
                                send_data[diary.owner] = updates
                            else:
                                updates = send_data[diary.owner]
                            updates.append(data)
        for owner, updates in send_data.items():
            Message.send_delivery_update(owner, updates)
        return count


class Setting:
    @staticmethod
    def exists():
        return app_models.GlobalSetting.objects.exists()

    @staticmethod
    def setting():
        return app_models.GlobalSetting.objects.first()

    @staticmethod
    def create_setting(**kwargs):
        if not Setting.exists():
            setting = app_models.GlobalSetting(**kwargs)
            app_models.GlobalSetting.save(setting)


class Statistics:
    OVERVIEW = 'overview'
    SEASON_TABLE = 'season_table'
    SEASON_CHART = 'season_chart'
    TIMELINE = 'timeline'
    TIMELINE_RECORD = 'timeline_record'

    @staticmethod
    def overview(profile, refresh=False):
        """
        获得概览数据报表。
        :param profile:
        :param refresh:
        :return:
        """
        if refresh:
            overview = statistics.generate_overview(profile)
            obj = app_models.Statistics.objects.filter(owner=profile, type=Statistics.OVERVIEW).first()
            if obj is not None:
                obj.content = overview
            else:
                obj = app_models.Statistics(owner=profile, type=Statistics.OVERVIEW, content=overview)
            obj.save()
            return obj
        else:
            return app_models.Statistics.objects.filter(owner=profile, type=Statistics.OVERVIEW).first()

    @staticmethod
    def season_table(profile, year, season, refresh=False):
        """
        获得或生成单季番剧统计表。
        :param profile:
        :param year:
        :param season:
        :param refresh: 是否强制重新生成统计表。
        :return:
        """
        key = statistics.get_season_key(year=year, season=season)
        obj = app_models.Statistics.objects.filter(owner=profile, type=Statistics.SEASON_TABLE, key=key).first()
        if refresh:
            data = statistics.generate_season_table(profile, year, season)
            # 将更新的数据刷新到本季的数据模型
            if obj is None:
                obj = app_models.Statistics(owner=profile, type=Statistics.SEASON_TABLE, key=key, content=data)
            else:
                obj.content = data
            obj.save()
            # 将更新的数据刷新到图表模型
            chart_json = {
                'season': key,
                'count': data['count'],
                'score_avg': data['score_avg'],
                'score_min': data['score_min'],
                'score_max': data['score_max'],
                'each_delay_avg': data['each_delay_avg'],
                'finish_delay_avg': data['finish_delay_avg'],
            }
            chart = app_models.Statistics.objects.filter(owner=profile, type=Statistics.SEASON_CHART).first()
            if chart is None:
                chart = app_models.Statistics(owner=profile, type=Statistics.SEASON_CHART, content={'seasons': [chart_json]})
            else:
                for i in range(0, len(chart.content['seasons'])):
                    if chart.content['seasons'][i]['season'] == key:
                        chart.content['seasons'][i] = chart_json
                        break
                else:
                    chart.content['seasons'].append(chart_json)
                    chart.content['seasons'].sort(key=lambda item: item['season'])
            chart.save()
        return obj

    @staticmethod
    def season_chart(profile, refresh=False):
        """
        获得季度统计坐标轴的数据报表。
        :param profile:
        :param refresh:
        :return:
        """
        if refresh:
            seasons = statistics.generate_season_chart(profile)
            obj = app_models.Statistics.objects.filter(owner=profile, type=Statistics.SEASON_CHART).first()
            if obj is not None:
                obj.content = {'seasons': seasons}
            else:
                obj = app_models.Statistics(owner=profile, type=Statistics.SEASON_CHART, content={'seasons': seasons})
            obj.save()
            return obj
        else:
            return app_models.Statistics.objects.filter(owner=profile, type=Statistics.SEASON_CHART).first()

    @staticmethod
    def timeline(profile, key, refresh_data=None):
        """
        获得时间线数据表。时间线表用一个key区分不同的报表。
        :param profile:
        :param key:
        :param refresh_data: 存在这个项时，对key项进行数据更新。
        :return:
        """
        if refresh_data is not None:
            if key is None:
                raise app_exceptions.ApiError('WrongKey', 'Key cannot be null.')
            mode = refresh_data.get('mode', None)
            if mode is not None:
                data = statistics.generate_timeline(profile, mode)
                if data is None:
                    raise app_exceptions.ApiError('WrongMode', 'Mode parameter is wrong.')
            else:
                data = None
            obj = app_models.Statistics.objects.filter(owner=profile, type=Statistics.TIMELINE, key=key).first()
            if obj is not None:
                obj.content = {'partitions': data if mode is not None else obj.content['partitions'],
                               'title': refresh_data.get('title', obj.content['title']),
                               'mode': mode or obj.content['mode']}
                # 更新记录表
                record = app_models.Statistics.objects.filter(owner=profile, type=Statistics.TIMELINE_RECORD).first()
                if refresh_data.get('title') is not None and record is not None:
                    for r in record.content['records']:
                        if r['key'] == key:
                            r['title'] = refresh_data.get('title')
                            record.save()
                            break
            else:
                if data is None:
                    raise app_exceptions.ApiError('WrongMode', 'Mode parameter is wrong.')
                obj = app_models.Statistics(owner=profile, type=Statistics.TIMELINE, key=key,
                                            content={'partitions': data,
                                                     'title': refresh_data.get('title', None),
                                                     'mode': mode})
                # 处理记录表
                record = app_models.Statistics.objects.filter(owner=profile, type=Statistics.TIMELINE_RECORD).first()
                new_record = {'key': key, 'title': obj.content['title']}
                if record is not None:
                    li = record.content.get('records', [])
                    li.append(new_record)
                    record.content['records'] = li
                else:
                    record = app_models.Statistics(owner=profile, type=Statistics.TIMELINE_RECORD,
                                                   content={'records': [new_record]})
                record.save()
            obj.save()
            return obj
        else:
            return app_models.Statistics.objects.filter(owner=profile, type=Statistics.TIMELINE, key=key).first()

    @staticmethod
    def timeline_record(profile):
        return app_models.Statistics.objects.filter(owner=profile, type=Statistics.TIMELINE_RECORD).first()
