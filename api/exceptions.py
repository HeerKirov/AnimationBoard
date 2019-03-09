from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, status


class AlreadyLogin(exceptions.PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Already login.')


class ApiError(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('A parse error occurred.')

    def __init__(self, code=None, detail=None, status_code=None, **kwargs):
        self.code = code if code is not None else None
        self.status_code = status_code if status_code is not None else self.status_code
        self.detail = {
            'detail': detail if detail is not None else self.default_detail,
            'code': self.code
        }
        if kwargs is not None:
            for k, v in kwargs:
                self.detail[k] = v

    def __str__(self):
        return self.detail['detail']
