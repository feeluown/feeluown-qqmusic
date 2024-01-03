import json
import logging
import os
from pathlib import Path

from feeluown.utils import aio
from feeluown.consts import DATA_DIR
from feeluown.gui.widgets.login import CookiesLoginDialog, InvalidCookies
from feeluown.gui.provider_ui import AbstractProviderUi
from feeluown.app.gui_app import GuiApp

from .provider import provider
from .excs import QQIOError

logger = logging.getLogger(__name__)


USER_INFO_FILE = DATA_DIR + '/qqmusic_user_info.json'


class ProviderUI(AbstractProviderUi):
    def __init__(self, app: GuiApp):
        self._app = app

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
            #    - url: https://xui.ptlogin2.qq.com/cgi-bin/xlogin?appid=1006102&daid=384&low_login=1&\
            #           pt_no_auth=1&s_url=https://y.qq.com/vip/daren_recruit/apply.html&style=40
            #    - keys: ['skey']
            url = os.getenv('FUO_QQMUSIC_LOGIN_URL', 'https://y.qq.com')
            keys = os.getenv('FUO_QQMUSIC_LOGIN_COOKIE_KEYS', 'qqmusic_key').split(',')
            self._dialog = LoginDialog(url, keys)
            self._dialog.login_succeed.connect(self.on_login_succeed)
            self._dialog.show()
            self._dialog.autologin()
        else:
            logger.info('already logged in')
            self.show_current_user()

    def on_login_succeed(self):
        self.show_current_user()
        del self._dialog

    def show_current_user(self):
        """
        please ensure user is logged in
        """
        user = provider._user
        self._app.ui.left_panel.playlists_con.show()

        async def _show_playlists():
            playlists = await aio.run_fn(lambda: user.playlists)
            fav_playlists = await aio.run_fn(lambda: user.fav_playlists)
            self._app.pl_uimgr.add(playlists)
            self._app.pl_uimgr.add(fav_playlists, is_fav=True)

        self._app.pl_uimgr.clear()
        aio.run_afn(_show_playlists)


class LoginDialog(CookiesLoginDialog):

    def setup_user(self, user):
        provider._user = user

    async def user_from_cookies(self, cookies):
        if not cookies:  # is None or empty
            raise InvalidCookies('empty cookies')

        uin = provider.api.get_uin_from_cookies(cookies)
        if uin is None:
            raise InvalidCookies("can't extract user info from cookies")

        provider.api.set_cookies(cookies)
        # try to extract current user
        try:
            user = await aio.run_in_executor(None, provider.User.get, uin)
        except QQIOError:
            provider.api.set_cookies(None)
            raise InvalidCookies('get user info with cookies failed, expired cookies?')
        else:
            return user

    def load_user_cookies(self):
        if os.path.exists(USER_INFO_FILE):
            # if the file is broken, just raise error
            with open(USER_INFO_FILE) as f:
                return json.load(f).get('cookies', None)

    def dump_user_cookies(self, user, cookies):
        js = {
            'identifier': user.identifier,
            'name': user.name,
            'cookies': cookies
        }
        with open(USER_INFO_FILE, 'w') as f:
            json.dump(js, f, indent=2)
