import logging

from fuocore.provider import AbstractProvider
from .api import API


logger = logging.getLogger(__name__)


class QQProvider(AbstractProvider):
    def __init__(self):
        super().__init__()
        self.api = API()

    @property
    def identifier(self):
        return 'qqmusic'

    @property
    def name(self):
        return 'QQ 音乐'


provider = QQProvider()


from .models import search  # noqa
provider.search = search
