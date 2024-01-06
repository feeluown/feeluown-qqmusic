import logging

from feeluown.library import AbstractProvider, ProviderV2, ProviderFlags as PF
from feeluown.models import ModelType
from feeluown.utils.reader import create_reader
from .api import API


logger = logging.getLogger(__name__)


class QQProvider(AbstractProvider, ProviderV2):
    class meta:
        identifier = 'qqmusic'
        name = 'QQ 音乐'
        flags = {
            ModelType.song: PF.similar,
            ModelType.none: PF.current_user,
        }

    def __init__(self):
        super().__init__()
        self.api = API()

    @property
    def identifier(self):
        return 'qqmusic'

    @property
    def name(self):
        return 'QQ 音乐'

    def rec_list_daily_songs(self):
        if not self.has_current_user():
            return
        return self._user.rec_songs

    def rec_list_daily_playlists(self):
        if not self.has_current_user():
            return
        return self._user.rec_playlists

    def current_user_fav_create_songs_rd(self):
        if self.has_current_user():
            return create_reader(self._user.fav_songs)
        return create_reader([])

    def current_user_fav_create_albums_rd(self):
        if self.has_current_user():
            return create_reader(self._user.fav_albums)
        return create_reader([])

    def current_user_fav_create_artists_rd(self):
        if self.has_current_user():
            return create_reader(self._user.fav_artists)
        return create_reader([])

    def current_user_fav_create_playlists_rd(self):
        if self.has_current_user():
            return create_reader(self._user.fav_playlists)
        return create_reader([])

    def has_current_user(self):
        return self._user is not None

    def song_list_similar(self, song):
        data_songs = self.api.song_similar(int(song.identifier))
        return [_deserialize(data_song, QQSongSchema)
                for data_song in data_songs]


provider = QQProvider()


from .schemas import QQSongSchema  # noqa
from .models import search, _deserialize  # noqa

provider.search = search
