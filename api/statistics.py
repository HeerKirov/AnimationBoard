from django.db import connection
from django.db.utils import DataError
from . import models as app_models, enums
from datetime import timedelta, datetime
import pytz
import config

BASE_TIMEZONE = config.BASIC_TIMEZONE


def generate_overview(profile):
    """
    生成全局概览。全局概览主要统计所有看过的番的一些泛用信息。
    :param profile:
    :return: {
        count: <看过/正在看的番的总数量>,
        limit_level: {
            <value>: <count>
        },
        tags: [
            {
                name: <标签名>,
                count: <标签出现过的数量>
            }
        ],
        score_avg: <平均分>,
        score:{
            <value>: <count>
        },
        original_work_type: {
            <value>: <count>
        },
        publish_type: {
            <value>: <count>
        }
    }
    """
    if not hasattr(profile, 'diaries'):
        return {}
    limit_level = {}
    tags = {}
    score_sum = 0
    score = {}
    original_work_type = {}
    publish_type = {}
    diaries = profile.diaries.exclude(status=enums.DiaryStatus.give_up).all()
    count = len(diaries)
    for diary in diaries:
        animation = diary.animation
        comment = app_models.Comment.objects.filter(animation=animation, owner=profile).first()
        if animation.limit_level is not None:
            if animation.limit_level in limit_level:
                limit_level[animation.limit_level] = limit_level[animation.limit_level] + 1
            else:
                limit_level[animation.limit_level] = 1
        if animation.original_work_type is not None:
            if animation.original_work_type in original_work_type:
                original_work_type[animation.original_work_type] = original_work_type[animation.original_work_type] + 1
            else:
                original_work_type[animation.original_work_type] = 1
        if animation.publish_type in publish_type:
            publish_type[animation.publish_type] = publish_type[animation.publish_type] + 1
        else:
            publish_type[animation.publish_type] = 1
        if comment is not None and comment.score is not None:
            score_sum += comment.score
            if comment.score in score:
                score[comment.score] = score[comment.score] + 1
            else:
                score[comment.score] = 1
        for tag in animation.tags.all():
            if tag.name in tags:
                tags[tag.name] = tags[tag.name] + 1
            else:
                tags[tag.name] = 1
    with connection.cursor() as cursor:
        cursor.execute("""
            select api_tag.name, count(*) as count
            from api_animation_tags aat
              inner join api_tag on api_tag.id = aat.tag_id
              inner join api_diary ad on ad.animation_id = aat.animation_id
            where ad.owner_id = %s
            group by api_tag.name order by count desc
        """, [profile.id])
        row = cursor.fetchall()
    tags_list = []
    for (tag, cnt) in row:
        tags_list.append({'name': tag, 'count': cnt})
    tags_list.sort(key=lambda i: -i['count'])
    return {
        'count': count,
        'limit_level': limit_level,
        'tags': tags_list,
        'score_avg': score_sum / count,
        'score': score,
        'original_work_type': original_work_type,
        'publish_type': publish_type
    }


def generate_season_chart(profile):
    """
    生成全部季度番剧的图表。
    这个功能实际上是season_table的附加功能，但是它一次性覆盖了全部的季度。
    :param profile: 生成主体的profile model。
    :return: [
        {
            count: <本季的追番数量>,
            score_avg: <本季平均分>,
            score_min: <本季最低分>,
            score_max: <本季最高分>,
            each_delay_avg: <平均每集观看延迟(小时)>,
            finish_delay_avg: <平均看完的延迟(小时)>
        }
    ]
    """
    if not hasattr(profile, 'diaries'):
        return []
    season_dict = dict()
    diaries = profile.diaries.filter(status__in=[enums.DiaryStatus.complete, enums.DiaryStatus.watching]).all()
    for diary in diaries:
        if diary.animation.publish_type == enums.AnimationPublishType.general and \
                diary.subscription_time is not None and \
                diary.animation.publish_time + timedelta(days=90) >= \
                (diary.subscription_time + timedelta(hours=BASE_TIMEZONE)).date():
            key = get_season_key(date=diary.animation.publish_time)
            if key is not None:
                comment = app_models.Comment.objects.filter(animation=diary.animation, owner=profile).first()
                if key in season_dict:
                    li = season_dict[key]
                else:
                    li = []
                    season_dict[key] = li
                li.append((diary, diary.animation, comment))
    # 处理
    seasons = []
    for (key, li) in season_dict.items():
        score_max, score_min, score_sum, score_count = None, None, 0, 0
        season_each_delay_sum, season_each_delay_count = 0, 0
        season_finish_delay_sum, season_finish_delay_count, season_finish_delay_max = 0, 0, 0
        for diary, animation, comment in li:
            finish_delay = get_finish_delay(animation, diary.finish_time) if diary.finish_time is not None else None
            if finish_delay is not None:
                if season_finish_delay_max is None or season_finish_delay_max < finish_delay:
                    season_finish_delay_max = finish_delay
                season_finish_delay_sum += finish_delay
                season_finish_delay_count += 1
            each_delay_sum, each_delay_count = 0, 0
            for delay in get_each_delay(animation.published_record, diary.watched_record):
                each_delay_sum += delay
                season_each_delay_sum += delay
                each_delay_count += 1
                season_each_delay_count += 1
            if comment is not None and comment.score is not None:
                if score_max is None or comment.score > score_max:
                    score_max = comment.score
                if score_min is None or comment.score < score_min:
                    score_min = comment.score
                score_sum += comment.score
                score_count += 1
        seasons.append({
            'season': key,
            'count': len(li),
            'score_max': score_max,
            'score_min': score_min,
            'score_avg': score_sum / score_count if score_count > 0 else None,
            'each_delay_avg': season_each_delay_sum / season_each_delay_count if season_each_delay_count > 0 else None,
            'finish_delay_avg': (season_finish_delay_sum - season_finish_delay_max) / (season_finish_delay_count - 1)
            if season_finish_delay_count > 1 else season_finish_delay_sum if season_finish_delay_count == 1 else None,
        })
    seasons.sort(key=lambda s: s['season'])
    return seasons


def generate_season_table(profile, year, season):
    """
    生成季度番剧概览表。这张表主要用于描述用户的某个季度追番信息。包括：
    - 该用户此季度看的番，以及在季内的一些统计数据，如数量、评分（包括上下限）、看番及时度。
    - 以季度为x轴的宏观统计数据，如每季的追番数量、平均评分、上下限评分、及时度评价等。当然这些数据只有当前季度的，需要取得数据后归纳。
    :param profile: 生成主体的profile model。
    :param year: 年份。
    :param season: 季度下标，取值范围是[0, 3]。
    :return: {
        count: <本季的追番数量>,
        score_avg: <本季平均分>,
        score_min: <本季最低分>,
        score_max: <本季最高分>,
        each_delay_avg: <平均每集观看延迟(小时)>,
        finish_delay_avg: <平均看完的延迟(小时)>
        tags: [
            {
                name: <tag name>,
                count: <count; 按这个字段降序排序>
            }, ...
        ],
        limit_level: {
            <limit level>: <count>, ...
        },
        animations: [
            {
                animation_id: <animation id>,
                title: <animation title>,
                cover: <animation cover>,
                limit_level: <animation limit_level>,
                score: <comment score; 没写则留null>,
                complete: <bool; 是否已经看完了。没有看完的会酌情加入统计>,
                finish_time: <diary finish_time; 列表按这个字段升序排序>,
                each_delay_avg: <平均每集观看延迟(小时)，要求有published_record和watched_record>,
                finish_delay: <看完的延迟(小时)，有watched_record时用它，没有时用publish_time估算>
            }, ...
        ]
    }
    """
    if not hasattr(profile, 'diaries'):
        return {}
    li = []
    diaries = profile.diaries.filter(animation__publish_time__year=year, animation__publish_time__month=season * 3 + 1,
                                     status__in=[enums.DiaryStatus.complete, enums.DiaryStatus.watching]).all()
    for diary in diaries:
        # 日记订阅时间在番剧发布后3个月内的，视作当季追番
        if diary.animation.publish_type == enums.AnimationPublishType.general and \
                diary.subscription_time is not None and \
                diary.animation.publish_time + timedelta(days=90) >= \
                (diary.subscription_time + timedelta(hours=BASE_TIMEZONE)).date():
            comment = app_models.Comment.objects.filter(animation=diary.animation, owner=profile).first()
            li.append((diary, diary.animation, comment))
    # 处理
    animations = []
    score_max, score_min, score_sum, score_count = None, None, 0, 0
    season_each_delay_sum, season_each_delay_count = 0, 0
    season_finish_delay_sum, season_finish_delay_count, season_finish_delay_max = 0, 0, 0
    tags_dict = {}
    limit_level_dict = {}
    # 逐个处理一季下的每一部动画
    for diary, animation, comment in li:
        finish_delay = get_finish_delay(animation, diary.finish_time) if diary.finish_time is not None else None
        if finish_delay is not None:
            if season_finish_delay_max is None or season_finish_delay_max < finish_delay:
                season_finish_delay_max = finish_delay
            season_finish_delay_sum += finish_delay
            season_finish_delay_count += 1
        each_delay_sum, each_delay_count = 0, 0
        for delay in get_each_delay(animation.published_record, diary.watched_record):
            each_delay_sum += delay
            season_each_delay_sum += delay
            each_delay_count += 1
            season_each_delay_count += 1
        if comment is not None and comment.score is not None:
            if score_max is None or comment.score > score_max:
                score_max = comment.score
            if score_min is None or comment.score < score_min:
                score_min = comment.score
            score_sum += comment.score
            score_count += 1
        animations.append({
            'animation_id': animation.id,
            'title': animation.title,
            'cover': animation.cover,
            'limit_level': animation.limit_level,
            'score': comment.score if comment is not None else None,
            'complete': diary.status == enums.DiaryStatus.complete,
            'finish_time': diary.finish_time.strftime('%Y-%m-%dT%H:%M:%SZ') if diary.finish_time is not None else None,
            'each_delay_avg': each_delay_sum / each_delay_count if each_delay_count > 0 else None,
            'finish_delay': finish_delay
        })
        for tag in animation.tags.all():
            if tag.name in tags_dict:
                tags_dict[tag.name] = tags_dict[tag.name] + 1
            else:
                tags_dict[tag.name] = 1
        if animation.limit_level is not None:
            if animation.limit_level in limit_level_dict:
                limit_level_dict[animation.limit_level] = limit_level_dict[animation.limit_level] + 1
            else:
                limit_level_dict[animation.limit_level] = 1
    animations.sort(key=lambda a: a['finish_time'] or '')
    tags = [{'name': tag, 'count': cnt} for (tag, cnt) in tags_dict.items()]
    tags.sort(key=lambda t: -t['count'])
    return {
        'count': len(li),
        'animations': animations,
        'score_max': score_max,
        'score_min': score_min,
        'score_avg': score_sum / score_count if score_count > 0 else None,
        'each_delay_avg': season_each_delay_sum / season_each_delay_count if season_each_delay_count > 0 else None,
        'finish_delay_avg': (season_finish_delay_sum - season_finish_delay_max) / (season_finish_delay_count - 1)
        if season_finish_delay_count > 1 else season_finish_delay_sum if season_finish_delay_count == 1 else None,
        'tags': tags,
        'limit_level': limit_level_dict
    }


def generate_timeline(profile, mode):
    """
    生成时间线。时间线按照时间区段统计时间轴上的看完数量，以及其他附加信息。
    :param profile:
    :param mode: 生成区段的模式。
        如果要使用自定义的区段，可以这么定义：[
            {
                label: <该区段的标记名称>,
                begin: <区段开始的date>,
                end: <区段结束的date，不包括在其中>
            }
        ]
    :return: [
        {
            label: <该区段的标记名称>,
            count: <finishTime落在这个区间内的番剧的数量>,
            sum_quantity: <finishTime落在这个区间内的番剧的集数总和>,
            sum_duration: <finishTime落在这个区间内的番剧的时长总和>
        }
    ]
    返回None时表示数据有错误。
    """
    if not hasattr(profile, 'diaries') or mode is None:
        return []
    result = []
    for partition in mode:
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                                select count(*) count, sum(aa.sum_quantity) quantity, sum(aa.sum_quantity * aa.duration)
                                from api_diary ad
                                  inner join api_animation aa on ad.animation_id = aa.id
                                where ad.owner_id = %s
                                  and ad.finish_time >= %s
                                  and ad.finish_time < %s;
                            """, [profile.id,
                                  partition.get('begin'),
                                  partition.get('end')])
            except DataError:
                return None
            count, quantity, duration = cursor.fetchone()
        result.append({
            'label': partition.get('label'),
            'count': count,
            'sum_quantity': quantity,
            'sum_duration': duration
        })
    return result


def get_season_key(date=None, year=None, season=None):
    """
    从date类型获得season key。
    :param date:
    :param year:
    :param season:
    :return:
    """
    if date is not None:
        season = {1: 0, 4: 1, 7: 2, 10: 3}.get(date.month, None)
        return '%s-%s' % (date.year, season) if season is not None else None
    elif year is not None and season is not None:
        return '%s-%s' % (year, season)
    else:
        return None


def get_each_delay(published_record, watched_record):
    """
    根据发布记录和观看记录迭代得到一个delay序列，单位是小时。
    :param published_record:
    :param watched_record:
    :return:
    """
    length = min(len(published_record), len(watched_record))
    for i in range(0, length):
        published_time = published_record[i]
        watched_time = watched_record[i]
        if published_time is not None and watched_time is not None and watched_time > published_time:
            delta = watched_time - published_time
            yield delta.days * 24 + delta.seconds // 3600


def get_finish_delay(animation, finish_time):
    if animation.published_quantity is not None and animation.sum_quantity is not None \
            and len(animation.published_record) >= animation.sum_quantity:
        last = animation.published_record[animation.sum_quantity - 1]
        if last is not None:
            delta = finish_time - last
            return delta.days * 24 + delta.seconds // 3600
    complete = datetime(year=animation.publish_time.year, month=animation.publish_time.month,
                        day=animation.publish_time.day, tzinfo=pytz.timezone('UTC'),
                        hour=0, minute=0, second=0) + timedelta(days=animation.sum_quantity * 7) - timedelta(hours=BASE_TIMEZONE)
    delta = finish_time - complete
    return delta.days * 24 + delta.seconds // 3600
