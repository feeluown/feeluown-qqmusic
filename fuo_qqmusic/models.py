import logging
import time
import base64

from fuocore.media import Quality, Media
from fuocore.models import cached_field

from fuocore.models import (
    BaseModel,
    SongModel,
    LyricModel,
    MvModel,
    PlaylistModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
    UserModel,
    SearchType
)

from fuocore.reader import RandomSequentialReader, SequentialReader

from .provider import provider
from .api import api
from .excs import QQIOError

logger = logging.getLogger(__name__)

def _deserialize(data, schema_cls, gotten=True):
    schema = schema_cls()
    obj = schema.load(data)
    # XXX: 将 model 设置为 gotten，减少代码编写时的心智负担，
    # 避免在调用 get 方法时进入无限递归。
    # if gotten:
    #     obj.stage = ModelStage.gotten
    return obj


class QQBaseModel(BaseModel):
    _api = provider.api

    class Meta:
        allow_get = True
        provider = provider
        fields = ('mid', )

    @classmethod
    def get(cls, identifier):

        raise NotImplementedError

class QQMvModel(MvModel, QQBaseModel):
    class Meta:
        support_multi_quality = True
        fields = ['q_url_mapping']

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_song_detail(identifier)
        vid = data['mv']['vid']
        mv_data = cls._api.get_mv(vid)['getMvUrl']['data']
        value_list = [i for i in mv_data.values()]
        if data is not None:
            mv = _deserialize(value_list[0], QQMvSchema)
            return mv
        return None

    def list_quality(self):
        return list(key for key, value in self.q_url_mapping.items()
                    if value is not None)

    def get_media(self, quality):
        if isinstance(quality, Quality.Video):  # Quality.Video Enum Item
            quality = quality.value
        return self.q_url_mapping.get(quality)


def create_g(func, schema=None):
    data = func()
    if data is None:
        raise QQIOError('server responses with error status code')

    count = int(data['total'])

    def read_func(start, end):
        data = func()
        return [_deserialize(data, schema)
                for data in data['list']]

    reader = RandomSequentialReader(count,
                                    read_func=read_func,
                                    max_per_read=200)
    return reader


class QQSongModel(SongModel, QQBaseModel):
    class Meta:
        fields = ('mid',)

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_song_detail(identifier)
        song = _deserialize(data, QQSongDetailSchema)

        return song

    @property
    def url(self):
        if self._url is not None and self._expired_at > time.time():
            return self._url
        url = self._api.get_song_url(self.mid)
        if url is not None:
            self._url = url
        else:
            self._url = ''
        return self._url

    @url.setter
    def url(self, url):
        self._expired_at = int(time.time()) + 60 * 10
        self._url = url

    @property
    def lyric(self):
        if self._lyric is not None:
            assert isinstance(self._lyric, LyricModel)
            return self._lyric
        data = self._api.get_lyric_by_songmid(self.mid)
        lyric = data.get('lyric', '')
        lyric = base64.b64decode(lyric).decode()
        self._lyric = LyricModel(
            identifier=self.identifier,
            content=lyric
        )
        return self._lyric
    
    @lyric.setter
    def lyric(self, value):
        self._lyric = value

    @property
    def mv(self):
        
        if self._mv is not None:
            return self._mv
        # 这里可能会先获取一次 mvid
        mv = QQMvModel.get(self.identifier)
        if mv is not None:
            self._mv = mv
            return self._mv
        
        return None

    @mv.setter
    def mv(self, value):
        self._mv = value


class QQAlbumModel(AlbumModel, QQBaseModel):
    class Meta:
        fields = ['mid']

    @classmethod
    def get(cls, identifier):
        data_album = cls._api.album_detail(identifier)
        if data_album is None:
            return None
        album = _deserialize(data_album, QQAlbumSchema)
        album.cover = cls._api.get_cover(album.mid, 2)
        return album

    @property
    def desc(self):
        if self._desc is None:
            self._desc = self._api.album_desc(self.identifier)
        return self._desc

    @desc.setter
    def desc(self, value):
        self._desc = value

class QQUserAlbumModel(PlaylistModel, QQBaseModel):
    class Meta:
        fields = ('uid',)
        allow_create_songs_g = True

    def create_songs_g(self):
        data = self._api.get_album_songs(self.mid)
        if data is None:
            raise QQIOError('server responses with error status code')
        
        song_list = data

        def read_func(start, end):

            songs = []
            for song in song_list:
                track = _deserialize(song, QQSongSchema)
                songs.append(track)
            return songs
        
        count = len(song_list)
        reader = RandomSequentialReader(count,
                                        read_func=read_func,
                                        max_per_read=200)
        return reader

class QQArtistModel(ArtistModel, QQBaseModel):
    class Meta:
        allow_create_songs_g = True
        allow_create_albums_g = True

    @classmethod
    def get(cls, identifier):
        data_artist = cls._api.artist_detail(identifier)
        artist = _deserialize(data_artist, QQArtistSchema)
        artist.cover = cls._api.get_cover(artist.mid, 1)
        return artist

    def create_songs_g(self):
        return create_g(self._api.artist_detail,
                        self.identifier,
                        _ArtistSongSchema)

    def create_albums_g(self):
        return create_g(self._api.artist_albums,
                        self.identifier,
                        _ArtistAlbumSchema)

class QQPlaylistModel(PlaylistModel, QQBaseModel):
    class Meta:
        fields = ('uid',)
        allow_create_songs_g = True

    def create_songs_g(self):
        data = self._api.get_playlist(self.identifier)
        if data is None:
            raise QQIOError('server responses with error status code')
        
        songlist = data

        count = songlist['cur_song_num']
        
        song_list = songlist['songlist']

        def read_func(start, end):
            songs = []
            for song in song_list[start:end]:
                track = _deserialize(song, QQSongSchema)
                songs.append(track)
            return songs

        reader = RandomSequentialReader(count,
                                        read_func=read_func,
                                        max_per_read=200)
        return reader

class QQSearchModel(SearchModel, QQBaseModel):
    pass

class QQUserModel(UserModel, QQBaseModel):
    class Meta:
        fields = ('cookies',)
        fields_no_get = ('cookies', 'rec_songs', 'rec_playlists',
                         'fav_artists', 'fav_albums', )

    @classmethod
    def get(cls, identifier):
        user = {'id': identifier}
        # user_brief = cls._api.user_brief(identifier)
        # user.update(user_brief)
        playlists = cls._api.user_playlists()['list']
        user['name'] = cls._api.get_user_info().json()['data']['creator']['nick']
        user['playlists'] = []
        user['fav_playlists'] = []
  
        for pl in playlists:
            user['playlists'].append( cls._api.get_playlist( pl['dissid'] ))
        
        # FIXME: GUI模式下无法显示歌单描述

        user = _deserialize(user, QQUserSchema)
        return user

    @cached_field()
    def rec_playlists(self):
        playlists_data = self._api.get_recommend_playlists()
        rec_playlists = []
        for playlist_data in playlists_data:
            # FIXME: GUI模式下无法显示歌单描述
            playlist_data['coverImgUrl'] = playlist_data['picUrl']
            playlist_data['description'] = None
            playlist = _deserialize(playlist_data, QQPlaylistSchema)
            rec_playlists.append(playlist)
        return rec_playlists

    @property
    def fav_artists(self):
        return create_g(self._api.user_favorite_artists, QQArtistSchema)

    @fav_artists.setter
    def fav_artists(self, _): pass

    @property
    def fav_albums(self):
        return create_g(self._api.user_favorite_albums, QQUserAlbumSchema)

    @fav_albums.setter
    def fav_albums(self, _): pass

    @cached_field()
    def rec_songs(self):
        songslist_id = self._api.get_recommend_songs()
        songlist = self._api.get_playlist(songslist_id)
        songs = songlist['songlist']
        if not songs == None:
            return [_deserialize(song_data, QQSongSchema)
                    for song_data in songs]

    def get_radio(self):
        songs_data = self._api.get_radio_music()
        if songs_data is None:
            logger.error('data should not be None')
            return None
        return [_deserialize(song_data, QQSongSchema)
                for song_data in songs_data]

def search(keyword, **kwargs):
    data_songs = provider.api.search(keyword)
    songs = []
    for data_song in data_songs:
        song = _deserialize(data_song, QQSongDetailSchema)
        songs.append(song)
    return QQSearchModel(songs=songs)

base_model = QQBaseModel()

from .schemas import (
    QQUserAlbumSchema,
    QQPlaylistSchema,
    QQMvSchema,
    QQUserSchema,
    QQSongSchema,
    QQSongDetailSchema,
    QQArtistSchema,
    QQAlbumSchema,
    _ArtistSongSchema,
    _ArtistAlbumSchema,
)  # noqa
