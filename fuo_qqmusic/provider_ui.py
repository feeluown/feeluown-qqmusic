import json
import logging
import os

from feeluown.utils.dispatch import Signal
from feeluown.utils.aio import run_fn
from feeluown.consts import DATA_DIR
from feeluown.gui.widgets.login import CookiesLoginDialog, InvalidCookies
from feeluown.gui.provider_ui import AbstractProviderUi
from feeluown.app.gui_app import GuiApp

from .provider import provider
from .excs import QQIOError
from .login import read_cookies, write_cookies

logger = logging.getLogger(__name__)


class ProviderUI(AbstractProviderUi):
    def __init__(self, app: GuiApp):
        self._app = app
        self._login_event = Signal()

    @property
    def provider(self):
        return provider

    def get_colorful_svg(self) -> str:
        return os.path.join(os.path.dirname(__file__), 'assets', 'icon.svg')

    def login_or_go_home(self):
        if provider._user is None:
            # According to #14, we have two ways to login:
            # 1. the default way, as the code shows
            # 2. a way for VIP user(maybe):
            #    - url: https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=1006102
            #           &daid=384&low_login=1&pt_no_auth=1
            #           &s_url=https://y.qq.com/vip/daren_recruit/apply.html&style=40
            #
            #    - keys: ['skey']
            url = os.getenv('FUO_QQMUSIC_LOGIN_URL', 'https://y.qq.com')
            keys = os.getenv('FUO_QQMUSIC_LOGIN_COOKIE_KEYS', 'qqmusic_key').split(',')
            self._dialog = LoginDialog(url, keys)
            self._dialog.login_succeed.connect(self.on_login_succeed)
            self._dialog.show()
            self._dialog.autologin()
        else:
            logger.info('already logged in')
            self.login_event.emit(self, 2)

    @property
    def login_event(self):
        return self._login_event

    def on_login_succeed(self):
        del self._dialog
        self.login_event.emit(self, 1)


class LoginDialog(CookiesLoginDialog):

    def setup_user(self, user):
        provider._user = user

    async def user_from_cookies(self, cookies):
        user, err = await run_fn(provider.try_get_user_from_cookies, cookies)
        if user:
            return user
        raise InvalidCookies(err)

    def load_user_cookies(self):
        return read_cookies()

    def dump_user_cookies(self, user, cookies):
        write_cookies(user, cookies)
