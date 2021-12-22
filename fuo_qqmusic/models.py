import logging

from feeluown.media import Quality, Media
from feeluown.models import (
    cached_field,
    BaseModel,
    SongModel,
    LyricModel,
    PlaylistModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
    MvModel,
    UserModel,
    ModelStage,
    SearchType,
)
from feeluown.utils.reader import SequentialReader, wrap as reader_wrap

from .provider import provider

logger = logging.getLogger(__name__)
UNFETCHED_MEDIA = object()


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
    total = int(data['totalNum'] if schema == _ArtistSongSchema else data['total'])

    def g():
        nonlocal data
        if data is None:
            yield from ()
        else:
            page = 1
            while data['songList'] if schema == _ArtistSongSchema else data['list']:
                obj_data_list = data['songList'] if schema == _ArtistSongSchema else data['list']
                for obj_data in obj_data_list:
                    obj = _deserialize(obj_data, schema, gotten=False)
                    # FIXME: 由于 feeluown 展示歌手的 album 列表时，
                    # 会依次同步的去获取 cover，所以我们这里必须先把 cover 初始化好，
                    # 否则 feeluown 界面会卡住
                    if schema == _BriefAlbumSchema:
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


class QQMvModel(MvModel, QQBaseModel):
    class Meta:
        fields = ['q_url_mapping']
        support_multi_quality = True

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_mv(identifier)
        if not data:
            return None
        fhd = hd = sd = ld = None
        for file in data['mp4']:
            if not file['url']:
                continue
            file_type = file['filetype']
            url = file['freeflow_url'][0]
            if file_type == 40:
                fhd = url
            elif file_type == 30:
                hd = url
            elif file_type == 20:
                sd = url
            elif file_type == 10:
                ld = url
            elif file_type == 0:
                pass
            else:
                logger.warning('There exists another quality:%s mv.', str(file_type))
        q_url_mapping = dict(fhd=fhd, hd=hd, sd=sd, ld=ld)
        return QQMvModel(identifier=identifier,
                         q_url_mapping=q_url_mapping)

    def list_quality(self):
        return list(key for key, value in self.q_url_mapping.items()
                    if value is not None)

    def get_media(self, quality):
        if isinstance(quality, Quality.Video):  # Quality.Video Enum Item
            quality = quality.value
        return self.q_url_mapping.get(quality)


class QQLyricModel(LyricModel, QQBaseModel):
    @classmethod
    def get(cls, identifier):
        content = cls._api.get_lyric_by_songmid(identifier)
        return cls(identifier=identifier, content=content)


class QQSongModel(SongModel, QQBaseModel):

    class Meta:
        fields = ('mid', 'media_id', 'mvid', 'q_media_mapping', 'quality_suffix')
        fields_no_get = ('mv', 'lyric', 'q_media_mapping')
        support_multi_quality = True

    @classmethod
    def get(cls, identifier):
        data = cls._api.song_detail(identifier)
        song = _deserialize(data, QQSongSchema)
        return song

    @cached_field()
    def lyric(self):
        return QQLyricModel.get(self.mid)

    @cached_field(ttl=100)
    def mv(self):
        if self.mvid is None:
            return None
        return QQMvModel.get(self.mvid)

    @cached_field(ttl=1000)
    def q_media_mapping(self):
        """fetch media info and save it in q_media_mapping"""
        q_media_mapping = {}
        if True:
            # 注：self.quality_suffix 这里可能会触发一次网络请求
            for idx, (q, t, b, s) in enumerate(self.quality_suffix):
                url = self._api.get_song_url_v2(self.mid, self.media_id, t)
                if url:
                    q_media_mapping[q] = Media(url, bitrate=b, format=s)
                    # 一般来说，高品质有权限 低品质也会有权限，减少网络请求。
                    # 这里把值设置为 UNFETCHED_MEDIA，作为一个标记。
                    for i in range(idx + 1, len(self.quality_suffix)):
                        q_media_mapping[self.quality_suffix[i][0]] = UNFETCHED_MEDIA
                    break
        else:
            q_urls_mapping = self._api.get_song_url(self.mid)
            q_bitrate_mapping = {'shq': 1000,
                                 'hq': 800,
                                 'sq': 500,
                                 'lq': 64}
            q_media_mapping = {}
            for quality, url in q_urls_mapping.items():
                bitrate = q_bitrate_mapping[quality]
                format = url.split('?')[0].split('.')[-1]
                q_media_mapping[quality] = Media(url, bitrate=bitrate, format=format)

        self.q_media_mapping = q_media_mapping
        return q_media_mapping

    @cached_field(ttl=600)
    def url(self):
        medias = list(self.q_media_mapping.values())
        if medias:
            return medias[0].url
        return ''

    def list_quality(self):
        return list(self.q_media_mapping.keys())

    def get_media(self, quality):
        media = self.q_media_mapping.get(quality)
        if media is UNFETCHED_MEDIA:
            for (q, t, b, s) in self.quality_suffix:
                if quality == q:
                    url = self._api.get_song_url_v2(self.mid, self.media_id, t)
                    if url:
                        media = Media(url, bitrate=b, format=s)
                        self.q_media_mapping[quality] = media
                    else:
                        media = None
                        self.q_media_mapping[quality] = None
                    break
            else:
                media = None
        return media


class QQAlbumModel(AlbumModel, QQBaseModel):
    class Meta:
        fields = ['mid']

    @classmethod
    def get(cls, identifier):
        data_album = cls._api.album_detail(identifier)
        if data_album is None:
            return None
        # FIXME: 目前专辑内的歌曲信息中 其MV信息为空, 且之后无法更新该信息
        album = _deserialize(data_album, QQAlbumSchema)
        album.cover = cls._api.get_cover(album.mid, 2)
        return album


class QQArtistModel(ArtistModel, QQBaseModel):
    class Meta:
        allow_create_songs_g = True
        allow_create_albums_g = True

    @classmethod
    def get(cls, identifier):
        data_mid = cls._api.artist_songs(identifier, 1, 0)['singerMid']
        data_artist = cls._api.artist_detail(data_mid)
        artist = _deserialize(data_artist, QQArtistSchema)
        artist.cover = cls._api.get_cover(artist.mid, 1)
        return artist

    def create_songs_g(self):
        return create_g(self._api.artist_songs,
                        self.identifier,
                        _ArtistSongSchema)

    def create_albums_g(self):
        return create_g(self._api.artist_albums,
                        self.identifier,
                        _BriefAlbumSchema)


class QQPlaylistModel(PlaylistModel, QQBaseModel):
    class Meta:
        allow_create_songs_g = True

    @classmethod
    def get(cls, identifier):
        data = cls._api.playlist_detail(identifier, limit=1000)
        return _deserialize(data, QQPlaylistSchema)

    def create_songs_g(self):
        # 歌单曲目数不能超过 1000，所以它可能不需要分页
        return reader_wrap(self.songs)


class QQSearchModel(SearchModel, QQBaseModel):
    pass


class QQUserModel(UserModel, QQBaseModel):
    class Meta:
        fields = ('cookies', 'fav_pid')
        fields_no_get = ('cookies', 'rec_songs', 'rec_playlists',
                         'fav_songs', 'fav_artists', 'fav_albums', )

    @classmethod
    def get(cls, identifier):
        data = cls._api.user_detail(identifier)
        data['creator']['fav_pid'] = data['mymusic'][0]['id']
        return _deserialize(data, QQUserSchema)

    @cached_field(ttl=5)  # ttl should be 0
    def fav_songs(self):
        # TODO: fetch more if total count > 100
        playlist = QQPlaylistModel.get(self.fav_pid)
        return playlist.songs

    @cached_field(ttl=5)  # ttl should be 0
    def fav_artists(self):
        # TODO: fetch more if total count > 100
        artists = self._api.user_favorite_artists(self.identifier, self.mid)
        return [_deserialize(artist, _UserArtistSchema, False) for artist in artists]

    @cached_field(ttl=5)  # ttl should be 0
    def fav_albums(self):
        # TODO: fetch more if total count > 100
        albums = self._api.user_favorite_albums(self.identifier)
        return [_deserialize(album, _UserAlbumSchema, False) for album in albums]

    @cached_field(ttl=5)  # ttl should be 0
    def fav_playlists(self):
        playlists = self._api.user_favorite_playlists(self.identifier, self.mid)
        return [_deserialize(playlist, QQPlaylistSchema, False) for playlist in playlists]

    @cached_field(ttl=5)  # ttl should be 0
    def rec_songs(self):
        pid = self._api.get_recommend_songs_pid()
        playlist = QQPlaylistModel.get(pid)
        return playlist.songs

    @cached_field(ttl=5)  # ttl should be 0
    def rec_playlists(self):
        pids = self._api.get_recommend_playlists_ids()
        # rec_playlists = [QQPlaylistModel.get(pid) for pid in pids]
        playlists = self._api.recommend_playlists()
        for pl in playlists:
            pl['dissid'] = pl['content_id']
            pl['dissname'] = pl['title']
            pl['logo'] = pl['cover']
        return [_deserialize(playlist, QQPlaylistSchema, False) for playlist in playlists]


def search(keyword, **kwargs):
    type_ = SearchType.parse(kwargs['type_'])
    if type_ == SearchType.pl:
        data = provider.api.search_playlists(keyword)
        playlists = [_deserialize(playlist, _BriefPlaylistSchema, False)
                     for playlist in data]
        return QQSearchModel(playlists=playlists)
    else:
        type_type_map = {
            SearchType.so: 0,
            SearchType.al: 8,
            SearchType.ar: 9,
        }
        data = provider.api.search(keyword, type_=type_type_map[type_])
        if type_ == SearchType.so:
            songs = [_deserialize(song, QQSongSchema) for song in data]
            return QQSearchModel(songs=songs)
        elif type_ == SearchType.al:
            albums = [_deserialize(album, _BriefAlbumSchema, False) for album in data]
            return QQSearchModel(albums=albums)
        else:
            artists = [_deserialize(artist, _BriefArtistSchema, False) for artist in data]
            return QQSearchModel(artists=artists)


base_model = QQBaseModel()

from .schemas import (  # noqa
    QQPlaylistSchema,
    QQUserSchema,
    QQSongSchema,
    QQArtistSchema,
    QQAlbumSchema,
    _ArtistSongSchema,
    _BriefAlbumSchema,
    _BriefArtistSchema,
    _BriefPlaylistSchema,
    _UserAlbumSchema,
    _UserArtistSchema,
)
