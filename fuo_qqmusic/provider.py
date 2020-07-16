import logging
from contextlib import contextmanager

from fuocore.provider import AbstractProvider
from .api import API


logger = logging.getLogger(__name__)


class QQProvider(AbstractProvider):
    def __init__(self):
        self.api = API()

        self._user = None

    @property
    def identifier(self):
        return 'qqmusic'

    @property
    def name(self):
        return 'QQ 音乐'

    # @contextmanager
    # def auth_as(self, user):
    #     old_user = self._user
    #     self.auth(user)
    #     try:
    #         yield
    #     finally:
    #         self.auth(old_user)

    def auth(self, user):
        self._user = user


provider = QQProvider()


from .models import search  # noqa
provider.search = search
