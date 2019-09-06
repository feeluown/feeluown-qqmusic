import logging
import re
import time

from fuocore.models import (
    BaseModel,
    SongModel,
    PlaylistModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
    ModelStage,
    GeneratorProxy,
)

from .provider import provider


logger = logging.getLogger(__name__)


class QQBaseModel(BaseModel):
    _api = provider.api

    class Meta:
        allow_get = True
        provider = provider
        fields = ('mid', )

    @classmethod
    def get(cls, identifier):
        raise NotImplementedError


def _deserialize(data, schema_cls, gotten=True):
    schema = schema_cls(strict=True)
    obj, _ = schema.load(data)
    # XXX: 将 model 设置为 gotten，减少代码编写时的心智负担，
    # 避免在调用 get 方法时进入无限递归。
    if gotten:
        obj.stage = ModelStage.gotten
    return obj


def create_g(func, identifier, schema):
    data = func(identifier, page=1)
    total = int(data['total'])

    def g():
        nonlocal data
        if data is None:
            yield from ()
        else:
            page = 1
            while data['list']:
                obj_data_list = data['list']
                for obj_data in obj_data_list:
                    obj = _deserialize(obj_data, schema, gotten=False)
                    # FIXME: 由于 feeluown 展示歌手的 album 列表时，
                    # 会依次同步的去获取 cover，所以我们这里必须先把 cover 初始化好，
                    # 否则 feeluown 界面会卡住
                    if schema == _ArtistAlbumSchema:
                        obj.cover = provider.api.get_cover(obj.mid, 2)
                    yield obj
                page += 1
                data = func(identifier, page)

    return GeneratorProxy(g(), total)


class QQSongModel(SongModel, QQBaseModel):
    class Meta:
        fields = ('mid', )

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_song_detail(identifier)
        song = _deserialize(data, QQSongSchema)
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


class QQAlbumModel(AlbumModel, QQBaseModel):
    class Meta:
        fields = ['mid']

    @classmethod
    def get(cls, identifier):
        data_album = cls._api.album_detail(identifier)
        album = _deserialize(data_album, QQAlbumSchema)
        album.cover = cls._api.get_cover(album.mid, 2)
        return album


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
    pass


class QQSearchModel(SearchModel, QQBaseModel):
    pass


def search(keyword, **kwargs):
    data_songs = provider.api.search(keyword)
    songs = []
    for data_song in data_songs:
        song = _deserialize(data_song, QQSongSchema)
        songs.append(song)
    return QQSearchModel(songs=songs)


from .schemas import (
    QQSongSchema,
    QQArtistSchema,
    QQAlbumSchema,
    _ArtistSongSchema,
    _ArtistAlbumSchema,
)  # noqa
