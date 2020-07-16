# import hashlib
# import json
import logging
# import os

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QVBoxLayout, QLineEdit,
                             QDialog, QPushButton,
                             QLabel)

# from .consts import USER_PW_FILE

logger = logging.getLogger(__name__)


class LoginDialog(QDialog):
    login_success = pyqtSignal([object])

    def __init__(self, verify_captcha=None, verify_userpw=None, create_user=None,
                 parent=None):
        super().__init__(parent)

        self.verify_captcha = verify_captcha
        self.verify_userpw = verify_userpw
        self.create_user = create_user

        self.is_encrypted = False
        self.captcha_needed = False
        self.captcha_id = 0

        self.cookie_input = QLineEdit(self)

        self.captcha_label = QLabel(self)
        self.captcha_label.hide()
        self.captcha_input = QLineEdit(self)
        self.captcha_input.hide()
        self.hint_label = QLabel(self)
        self.ok_btn = QPushButton('登录', self)
        self._layout = QVBoxLayout(self)

        self.cookie_input.setPlaceholderText('cookies(格式 a=_a; b=_b; ... ')

        self.ok_btn.clicked.connect(self.login)

        self.setFixedWidth(200)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addWidget(self.cookie_input)
        self._layout.addWidget(self.captcha_label)
        self._layout.addWidget(self.captcha_input)
        self._layout.addWidget(self.hint_label)
        self._layout.addWidget(self.ok_btn)

    def fill(self, data):
        self.cookie_input.setText(data['cookie'])

        self.is_encrypted = True

    def show_hint(self, text):
        self.hint_label.setText(text)

    @property
    def data(self):
        cookie = self.cookie_input.text()
        # pw = self.pw_input.text()
        # if self.is_encrypted:
        #     password = pw
        # else:
        #     password = hashlib.md5(pw.encode('utf-8')).hexdigest()
        d = dict(cookie=cookie)
        return d

    def captcha_verify(self, data):
        self.captcha_needed = True
        self.captcha_id = data['captcha_id']
        self.captcha_input.show()
        self.captcha_label.show()
        # FIXME: get pixmap from url
        # self._app.pixmap_from_url(url, self.captcha_label.setPixmap)

    def dis_encrypt(self, text):
        self.is_encrypted = False

    def login(self):
        if self.captcha_needed:
            captcha = str(self.captcha_input.text())
            captcha_id = self.captcha_id
            data = self.check_captcha(captcha_id, captcha)
            if data['code'] == 200:
                self.captcha_input.hide()
                self.captcha_label.hide()
            else:
                self.captcha_verify(data)

        user_data = self.data

        self.show_hint('正在登录...')

        login_response = self.verify_userpw(user_data['cookie'])

        if login_response.status_code == 200:
            user = self.create_user()
            self.login_success.emit(user)
            self.captcha_input.hide()
            self.captcha_label.hide()
            self.hide()
