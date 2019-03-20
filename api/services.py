from django.utils import timezone
from . import models as app_models, enums, utils
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
        animations = app_models.Animation.objects.all()
        send_data = {}
        count = 0
        for animation in animations:
            if len(animation.publish_plan) > 0 and animation.sum_quantity is not None:
                published_count, new_plan = animation.take_published_count()
                if published_count > 0:
                    count += 1
                    old_quantity = animation.published_quantity
                    if animation.published_quantity is None:
                        animation.published_quantity = 0
                    animation.publish_plan = new_plan
                    animation.published_quantity += published_count
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
                        animation.diaries.update(published_quantity=animation.published_quantity)
                        for diary in animation.diaries.all():
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
