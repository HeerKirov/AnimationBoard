from django.core.management.base import BaseCommand
from api import services


class Command(BaseCommand):
    help = 'Update all deliverys\' publish plan.'

    def handle(self, *args, **kwargs):
        self.stdout.write('Refresh %s delivery(s).' % (services.Animation.refresh_published(),))
        self.stdout.write('Successfully updated publish plan.')
