from django.core.management.base import BaseCommand
from api import models as app_models, relations as app_relations
from AnimationBoard.settings import COVER_DIRS
from PIL import Image
import os


class Command(BaseCommand):
    help = 'Translate all png image to jpeg image.'

    def handle(self, *args, **kwargs):
        cnt = 0
        for animation in app_models.Animation.objects.all():
            if animation.cover is not None and animation.cover.endswith('.png'):
                old_cover_name = animation.cover
                new_cover_name = animation.cover[:len(animation.cover) - 4] + '.jpg'
                animation.cover = new_cover_name
                animation.save()
                updated = set()
                app_relations.spread_cache_field(animation.id, animation.relations,
                                                 lambda id_list: app_models.Animation.objects.filter(id__in=id_list).
                                                 all(), 'cover', new_cover_name,
                                                 lambda i: updated.add(i))
                for item in updated:
                    item.save()
                if os.path.exists(COVER_DIRS + '/' + old_cover_name):
                    Image.open(COVER_DIRS + '/' + old_cover_name).convert('RGB').save(COVER_DIRS + '/' + new_cover_name)
                    os.remove(COVER_DIRS + '/' + old_cover_name)
                cnt += 1
        print('%s image was updated.' % (cnt,))
