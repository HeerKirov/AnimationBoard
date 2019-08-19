from django.core.management.base import BaseCommand
from AnimationBoard.settings import COVER_DIRS
from api.oss import bucket
import os


class Command(BaseCommand):
    help = 'Transform all local fs cover to oss.'

    def handle(self, *args, **kwargs):
        cnt = 0
        for parent, _, filenames in os.walk(COVER_DIRS):
            for filename in filenames:
                file_path = os.path.join(parent, filename)
                bucket.put_object_from_file(filename, file_path)
                cnt += 1
                print('[%s] uploaded.' % (filename,))
        print('%s image was uploaded.' % (cnt,))
