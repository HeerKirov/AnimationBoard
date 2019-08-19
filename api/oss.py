import oss2
import config
import time

if config.COVER_STORAGE['TYPE'] == 'oss':
    auth = oss2.Auth(config.COVER_STORAGE['OSS']['access_key_id'], config.COVER_STORAGE['OSS']['access_key_secret'])
    bucket = oss2.Bucket(auth, config.COVER_STORAGE['OSS']['endpoint'], config.COVER_STORAGE['OSS']['bucket_name'])
else:
    bucket = None


sign_url_cache = dict()
sign_timeout_cache = dict()


def sign_url(file_name):
    now = time.time()
    url = None
    if file_name in sign_url_cache:
        timeout = sign_timeout_cache.get(file_name)
        if timeout < now:
            url = sign_url_cache.get(file_name)
    if url is None:
        url = bucket.sign_url('GET', file_name, config.COVER_STORAGE['OSS']['sign_timeout'])
        timeout = now + config.COVER_STORAGE['OSS']['sign_timeout']
        sign_timeout_cache[file_name] = timeout
        sign_url_cache[file_name] = url
    return url
