import json
import logging
import os

from .api import api
from .schemas import QQUserSchema
from .models import _deserialize, base_model
from .consts import USERS_INFO_FILE

logger = logging.getLogger(__name__)


def create_user(user_info):
    name = user_info.json()['data']['creator']['nick']
    user = _deserialize(dict(
        name=name
    ), QQUserSchema)
    return user


class LoginController(object):
    _api = api

    def __init__(self, cookie, uid, name, img):
        super().__init__()
        self.cookie = cookie
        self.uid = uid
        self.name = name
        self.uin = ""

    @classmethod
    def create(cls):
        user_info = cls._api.get_user_info()
        return create_user(user_info)

    @classmethod
    def cookie_to_dict(cls, cookie):
        return {item.split('=')[0]: item.split('=')[1] for item in cookie.split('; ')}

    @classmethod
    def check(cls, cookie):
        # data = cls._api.login(cookie, pw)
        base_model._api.set_cookie(cookie)
        cls._api.set_cookie(cookie)
        cookie_dict = cls.cookie_to_dict(cookie)
        base_model._api.set_uin(
            cookie_dict['wxuin'] if 'wxuin' in cookie_dict else cookie_dict['uin'])
        cls._api.set_uin(
            cookie_dict['wxuin'] if 'wxuin' in cookie_dict else cookie_dict['uin'])
        cls._api.uin.replace('o', '')
        return cls._api.get_user_info()

    @classmethod
    def check_captcha(cls, captcha_id, text):
        flag, cid = cls._api.confirm_captcha(captcha_id, text)
        if flag is not True:
            url = cls._api.get_captcha_url(cid)
            return {'code': 415, 'message': '验证码错误',
                    'captcha_url': url, 'captcha_id': cid}
        return {'code': 200, 'message': '验证码正确'}

    @classmethod
    def save(cls, user):
        with open(USERS_INFO_FILE, 'w+') as f:
            data = {
                user.name: {
                    'uid': user.identifier,
                    'name': user.name,
                    'cookies': user.cookies
                }
            }
            if f.read() != '':
                data.update(json.load(f))
            json.dump(data, f, indent=4)

    @classmethod
    def load(cls):
        if not os.path.exists(USERS_INFO_FILE):
            return None
        with open(USERS_INFO_FILE, 'r') as f:
            text = f.read()
            if text == '':
                return None
            data = json.loads(text)
            cookie = next(iter(data.keys()))
            # self.cookie = data[cookie]
            user_data = data[cookie]
            uid = user_data['uid']
            name = user_data['name']
            cookies = user_data.get('cookies', cls._api.cookies)
            user = create_user(uid, name, cookies)
        return user
