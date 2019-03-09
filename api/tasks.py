from . import services


def delivery_publish_task():
    services.Animation.refresh_published()
