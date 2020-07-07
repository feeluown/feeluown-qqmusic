import json
from pathlib import Path
import re

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QPlainTextEdit


class QQMusicAuthenticator(QDialog):
    COOKIE_FILE = Path.home() / '.FeelUOwn' / 'data' / 'qqmusic-cookie.json'

    QQ_LOGIN = 'https://xui.ptlogin2.qq.com/cgi-bin/xlogin?daid=384&pt_no_auth=1&style=11&appid=1006102&s_url=https' \
               '%3A%2F%2Fy.qq.com%2Fportal%2Fprofile.html%23sub%3Dsinger%26tab%3Dfocus%26stat%3Dy_new.top.user_pic' \
               '%26stat%3Dy_new.top.pop.logout&low_login=1&hln_css=&hln_title=&hln_acc=&hln_pwd=&hln_u_tips=&hln_p_' \
               'tips=&hln_autologin=&hln_login=&hln_otheracc=&hide_close_icon=1&hln_qloginacc=&hln_reg=&hln_vctitle=' \
               '&hln_verifycode=&hln_vclogin=&hln_feedback='
    WX_LOGIN = 'https://open.weixin.qq.com/connect/qrconnect?appid=wx48db31d50e334801&redirect_uri=https%3A%2F%2Fy' \
               '.qq.com%2Fportal%2Fwx_redirect.html%3Flogin_type%3D2%26surl%3Dhttps%3A%2F%2Fy.qq.com%2F&response_t' \
               'ype=code&scope=snsapi_login&state=STATE&href=https%3A%2F%2Fy.gtimg.cn%2Fmediastyle%2Fyqq%2Fpopup_' \
               'wechat.css#wechat_redirect'

    def load_cookie(self):
        with open(self.COOKIE_FILE.as_posix(), 'r') as f:
            self.cookie_data = json.loads(f.read())

    def proceed_login(self, _):
        if self.cookie_data:
            self.done()
            return
        cookie_data = {}
        str_arr = re.split(r'\s+', self.cookie.toPlainText())
        for row in str_arr:
            d = row.split('=')
            if len(d) < 2:
                continue
            cookie_data[d[0]] = d[1].rstrip(';')
        with open(self.COOKIE_FILE.as_posix(), 'w') as f:
            f.write(json.dumps(cookie_data))
            f.flush()
        self.load_cookie()
        self.accept()

    def __init__(self):
        super().__init__()
        self.cookie_data = None
        if self.COOKIE_FILE.exists():
            self.load_cookie()
        layout = QVBoxLayout()
        wx_login = QLabel(f'<a href="{self.QQ_LOGIN}">QQ 登录</a>')
        qq_login = QLabel(f'<a href="{self.WX_LOGIN}">WX 登录</a>')
        self.cookie = QPlainTextEdit()
        self.cookie.setMaximumHeight(100)
        self.cookie.setPlaceholderText('cookie string')
        self.login_btn = QPushButton('Login')
        wx_login.setOpenExternalLinks(True)
        qq_login.setOpenExternalLinks(True)
        layout.addWidget(wx_login)
        layout.addWidget(qq_login)
        layout.addWidget(self.cookie)
        layout.addWidget(self.login_btn)
        self.login_btn.clicked.connect(self.proceed_login) # noqa
        self.setLayout(layout)
