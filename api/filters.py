import django_filters
from django_filters.constants import EMPTY_VALUES
from django import forms
from . import models as app_models


class EachSearchFilter(django_filters.Filter):
    """
    用于任意型匹配搜索。
    value将是一组序列。一般应当是list。但是是str时，会按照空格分裂。
    这个匹配要求这个序列中的每一项都能在指定的查询中找到一次匹配。
    """
    field_class = forms.CharField

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if isinstance(value, str):
            array = value.split(' ')
        elif isinstance(value, list):
            array = value
        else:
            array = []
        if len(array) <= 0:
            return qs
        if self.distinct:
            qs = qs.distinct()
        result = None
        for key in array:
            lookup = '%s__%s' % (self.field_name, self.lookup_expr)
            if result is None:
                result = self.get_method(qs)(**{lookup: key})
            else:
                result = result & self.get_method(qs)(**{lookup: key})
        return result


class ArrayFilter(django_filters.Filter):
    """将参数解析成列表。解析的规则是按空格分割."""
    field_class = forms.CharField

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if isinstance(value, str):
            array = value.split(' ')
        elif isinstance(value, list):
            array = value
        else:
            array = []
        if len(array) <= 0:
            return qs
        if self.distinct:
            qs = qs.distinct()
        lookup = '%s__%s' % (self.field_name, self.lookup_expr)
        return self.get_method(qs)(**{lookup: array})


class Database:
    class Animation(django_filters.FilterSet):
        original_work_type = django_filters.CharFilter(lookup_expr='iexact')
        publish_type = django_filters.CharFilter(lookup_expr='iexact')
        publish_time__ge = django_filters.DateFilter(field_name='publish_time', lookup_expr='ge')
        publish_time__le = django_filters.DateFilter(field_name='publish_time', lookup_expr='le')
        limit_level = django_filters.CharFilter(lookup_expr='iexact')
        tags__name = EachSearchFilter(field_name='tags__name', lookup_expr='iexact')
        original_work_authors = django_filters.NumberFilter(field_name='original_work_authors__id', lookup_expr='exact')
        staff_companies = django_filters.NumberFilter(field_name='staff_companies__id', lookup_expr='exact')
        staff_supervisors = django_filters.NumberFilter(field_name='staff_supervisors__id', lookup_expr='exact')

        class Meta:
            model = app_models.Animation
            fields = ('original_work_type', 'publish_type', 'publish_time__ge', 'publish_time__le', 'limit_level',
                      'tags__name', 'staff_supervisors', 'staff_companies', 'original_work_authors')


class Personal:
    class Diary(django_filters.FilterSet):
        title = django_filters.CharFilter()
        status = django_filters.CharFilter()
        status__in = ArrayFilter(field_name='status', lookup_expr='in')
        watch_many_times = django_filters.BooleanFilter()
        watch_original_work = django_filters.BooleanFilter()

        class Meta:
            model = app_models.Diary
            fields = ('title', 'status', 'status__in', 'watch_many_times', 'watch_original_work')
