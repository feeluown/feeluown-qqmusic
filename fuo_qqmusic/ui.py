import json
import logging
import os
from pathlib import Path

from fuocore import aio
from feeluown.consts import DATA_DIR
from feeluown.gui.widgets.login import CookiesLoginDialog, InvalidCookies

from .provider import provider
from .excs import QQIOError

logger = logging.getLogger(__name__)


USER_INFO_FILE = DATA_DIR + '/qqmusic_user_info.json'


class UiManager:
    def __init__(self, app):
        self._app = app
        self._pvd_item = app.pvd_uimgr.create_item(
            name=provider.identifier,
            text='QQ 音乐',
            symbol='♫ ',
            desc='点击登录 QQ 音乐',
            colorful_svg=str(Path(__file__).resolve().parent /
                             'assets' / 'icon.svg'),
        )
        self._pvd_item.clicked.connect(self.login_or_show)
        app.pvd_uimgr.add_item(self._pvd_item)

    def login_or_show(self):
        if provider._user is None:
            self._dialog = LoginDialog('https://y.qq.com', ['qqmusic_key'])
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
        self._app.ui.left_panel.my_music_con.hide()
        self._app.ui.left_panel.playlists_con.show()
        self._app.pl_uimgr.clear()
        self._app.pl_uimgr.add(user.playlists)
        self._pvd_item.text = f'QQ 音乐 - {user.name}'


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
