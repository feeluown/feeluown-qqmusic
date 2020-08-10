import logging

from fuocore.models import cached_field

from fuocore.models import (
    BaseModel,
    SongModel,
    PlaylistModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
    UserModel,
    ModelStage,
)

from fuocore.reader import SequentialReader, wrap as reader_wrap

from .provider import provider

logger = logging.getLogger(__name__)


def _deserialize(data, schema_cls, gotten=True):
    schema = schema_cls()
    obj = schema.load(data)
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

    return SequentialReader(g(), total)


class QQBaseModel(BaseModel):
    _api = provider.api

    class Meta:
        allow_get = True
        provider = provider
        fields = ('mid', )

    @classmethod
    def get(cls, identifier):

        raise NotImplementedError


class QQSongModel(SongModel, QQBaseModel):
    class Meta:
        fields = ('mid',)
        fields_no_get = ('mv', 'lyric')

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_song_detail(identifier)
        song = _deserialize(data, QQSongSchema)
        return song

    @cached_field(ttl=600)
    def url(self):
        url = self._api.get_song_url(self.mid)
        return url


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
        allow_create_songs_g = True

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_playlist(identifier)
        return _deserialize(data, QQPlaylistSchema)

    def create_songs_g(self):
        # 歌单曲目数不能超过 1000，所以它可能不需要分页
        return reader_wrap(self.songs)


class QQSearchModel(SearchModel, QQBaseModel):
    pass


class QQUserModel(UserModel, QQBaseModel):
    class Meta:
        fields = ('cookies',)
        fields_no_get = ('cookies', 'rec_songs', 'rec_playlists',
                         'fav_artists', 'fav_albums', )

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_user_info(identifier)
        return _deserialize(data, QQUserSchema)

    @cached_field(ttl=5)  # ttl should be 0
    def fav_albums(self):
        # TODO: fetch more if total count > 100
        albums = self._api.user_favorite_albums(self.identifier)
        return [_deserialize(album, QQAlbumSchema) for album in albums]

    @cached_field(ttl=5)  # ttl should be 0
    def rec_songs(self):
        pid = self._api.get_recommend_songs_pid()
        playlist = QQPlaylistModel.get(pid)
        return playlist.songs


def search(keyword, **kwargs):
    data_songs = provider.api.search(keyword)
    songs = []
    for data_song in data_songs:
        song = _deserialize(data_song, QQSongSchema)
        songs.append(song)
    return QQSearchModel(songs=songs)


base_model = QQBaseModel()

from .schemas import (  # noqa
    QQPlaylistSchema,
    QQUserSchema,
    QQSongSchema,
    QQArtistSchema,
    QQAlbumSchema,
    _ArtistSongSchema,
    _ArtistAlbumSchema,
)
