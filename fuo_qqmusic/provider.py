import logging
from typing import List, Optional, Protocol
from feeluown.excs import ModelNotFound
from feeluown.library import (
    AbstractProvider,
    ProviderV2,
    ProviderFlags as PF,
    SupportsSongGet,
    SupportsSongMultiQuality,
    SupportsSongMV,
    VideoModel,
    LyricModel,
    SupportsCurrentUser,
    SupportsVideoGet,
    SupportsSongLyric,
    SupportsAlbumGet,
    SupportsArtistGet,
    SupportsPlaylistGet,
    SupportsPlaylistSongsReader,
    SimpleSearchResult,
    SearchType,
    ModelType,
)
from feeluown.media import Media, Quality
from feeluown.utils.reader import create_reader, SequentialReader
from .api import API


logger = logging.getLogger(__name__)
UNFETCHED_MEDIA = object()
SOURCE = "qqmusic"


class Supports(
    SupportsSongGet,
    SupportsSongMultiQuality,
    SupportsSongMV,
    SupportsCurrentUser,
    SupportsVideoGet,
    SupportsSongLyric,
    SupportsAlbumGet,
    SupportsArtistGet,
    SupportsPlaylistGet,
    SupportsPlaylistSongsReader,
    Protocol,
):
    pass


class QQProvider(AbstractProvider, ProviderV2):
    class meta:
        identifier = "qqmusic"
        name = "QQ 音乐"
        flags = {
            ModelType.song: PF.similar,
            ModelType.none: PF.current_user,
        }

    def __init__(self):
        super().__init__()
        self.api = API()

    def _(self) -> Supports:
        return self

    @property
    def identifier(self):
        return "qqmusic"

    @property
    def name(self):
        return "QQ 音乐"

    def use_model_v2(self, mtype):
        return mtype in (
            ModelType.song,
            ModelType.album,
            ModelType.artist,
            ModelType.playlist,
        )

    def song_get(self, identifier):
        data = self.api.song_detail(identifier)
        return _deserialize(data, QQSongSchema)

    def song_get_mv(self, song):
        mv_id = self._model_cache_get_or_fetch(song, "mv_id")
        if mv_id == 0:
            return None
        video = self.video_get(mv_id)
        # mv 的名字是空的
        video.title = song.title
        return video

    def song_get_lyric(self, song):
        mid = self._model_cache_get_or_fetch(song, "mid")
        content = self.api.get_lyric_by_songmid(mid)
        return LyricModel(identifier=mid, source=SOURCE, content=content)

    def video_get(self, identifier):
        data = self.api.get_mv(identifier)
        if not data:
            raise ModelNotFound(f"mv:{identifier} not found")
        fhd = hd = sd = ld = None
        for file in data["mp4"]:
            if not file["url"]:
                continue
            file_type = file["filetype"]
            url = file["freeflow_url"][0]
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
                logger.warning("There exists another quality:%s mv.", str(file_type))
        q_url_mapping = dict(fhd=fhd, hd=hd, sd=sd, ld=ld)
        video = VideoModel(
            identifier=identifier,
            source=SOURCE,
            title="未知名字",
            artists=[],
            duration=1,
            cover="",
        )
        video.cache_set("q_url_mapping", q_url_mapping)
        return video

    def video_get_media(self, video, quality):
        q_media_mapping = self._model_cache_get_or_fetch(video, "q_url_mapping")
        return Media(q_media_mapping[quality.value])

    def video_list_quality(self, video):
        q_media_mapping = self._model_cache_get_or_fetch(video, "q_url_mapping")
        return [Quality.Video(k) for k, v in q_media_mapping.items() if v]

    def song_list_quality(self, song) -> List[Quality.Audio]:
        """List all possible qualities

        Please ensure all the qualities are valid. `song_get_media(song, quality)`
        must not return None with a valid quality.
        """
        return list(self._song_get_q_media_mapping(song))

    def song_get_media(self, song, quality: Quality.Audio) -> Optional[Media]:
        """Get song's media by a specified quality

        :return: when quality is invalid, return None
        """
        q_media_mapping = self._song_get_q_media_mapping(song)
        quality_suffix = song.cache_get("quality_suffix")
        mid = song.cache_get("mid")
        media_id = song.cache_get("media_id")
        media = q_media_mapping.get(quality)
        if media is UNFETCHED_MEDIA:
            for q, t, b, s in quality_suffix:
                if quality == q:
                    url = self.api.get_song_url_v2(mid, media_id, t)
                    if url:
                        media = Media(url, bitrate=b, format=s)
                        q_media_mapping[quality] = media
                    else:
                        media = None
                        q_media_mapping[quality] = None
                    break
            else:
                media = None
        return media

    def _song_get_q_media_mapping(self, song):
        q_media_mapping, exists = song.cache_get("q_media_mapping")
        if exists is True:
            return q_media_mapping
        quality_suffix = self._model_cache_get_or_fetch(song, "quality_suffix")
        mid = self._model_cache_get_or_fetch(song, "mid")
        media_id = self._model_cache_get_or_fetch(song, "media_id")
        q_media_mapping = {}
        # 注：self.quality_suffix 这里可能会触发一次网络请求
        for idx, (q, t, b, s) in enumerate(quality_suffix):
            url = self.api.get_song_url_v2(mid, media_id, t)
            if url:
                q_media_mapping[Quality.Audio(q)] = Media(url, bitrate=b, format=s)
                # 一般来说，高品质有权限 低品质也会有权限，减少网络请求。
                # 这里把值设置为 UNFETCHED_MEDIA，作为一个标记。
                for i in range(idx + 1, len(quality_suffix)):
                    q_media_mapping[
                        Quality.Audio(quality_suffix[i][0])
                    ] = UNFETCHED_MEDIA
                break
        song.cache_set("q_media_mapping", q_media_mapping)
        return q_media_mapping

    def artist_get(self, identifier):
        data_mid = self.api.artist_songs(int(identifier), 1, 0)["singerMid"]
        data_artist = self.api.artist_detail(data_mid)
        artist = _deserialize(data_artist, QQArtistSchema)
        return artist

    def artist_create_songs_rd(self, artist):
        return create_g(
            self.api.artist_songs, int(artist.identifier), _ArtistSongSchema
        )

    def artist_create_albums_rd(self, artist):
        return create_g(
            self.api.artist_albums, int(artist.identifier), _BriefAlbumSchema
        )

    def album_get(self, identifier):
        data_album = self.api.album_detail(int(identifier))
        if data_album is None:
            raise ModelNotFound
        album = _deserialize(data_album, QQAlbumSchema)
        return album

    def user_get(self, identifier):
        data = self.api.user_detail(identifier)
        data["creator"]["fav_pid"] = data["mymusic"][0]["id"]
        # 假设使用微信登陆，从网页拿到 cookie，cookie 里面的 uin 是正确的，
        # 而这个接口返回的 uin 则可能是 0，因此手动重置一下。
        data["creator"]["uin"] = identifier
        return _deserialize(data, QQUserSchema)

    def playlist_get(self, identifier):
        data = self.api.playlist_detail(int(identifier), limit=1000)
        return _deserialize(data, QQPlaylistSchema)

    def playlist_create_songs_rd(self, playlist):
        songs = self._model_cache_get_or_fetch(playlist, "songs")
        return create_reader(songs)

    def rec_list_daily_playlists(self):
        user = self.get_current_user()
        if user is None:
            return []
        # pids = self.api.get_recommend_playlists_ids()
        # rec_playlists = [QQPlaylistModel.get(pid) for pid in pids]
        playlists = self.api.recommend_playlists()
        for pl in playlists:
            pl["dissid"] = pl["content_id"]
            pl["dissname"] = pl["title"]
            pl["logo"] = pl["cover"]
        return [_deserialize(playlist, QQPlaylistSchema) for playlist in playlists]

    def current_user_list_playlists(self):
        user = self.get_current_user()
        if user is None:
            return []
        playlists = self._model_cache_get_or_fetch(user, "playlists")
        return playlists

    def current_user_fav_create_songs_rd(self):
        user = self.get_current_user()
        if user is None:
            return create_reader([])
        fav_pid = self._model_cache_get_or_fetch(user, "fav_pid")
        playlist = self.playlist_get(fav_pid)
        reader = create_reader(self.playlist_create_songs_rd(playlist))
        return reader.readall()

    def current_user_fav_create_albums_rd(self):
        user = self.get_current_user()
        if user is None:
            return create_reader([])
        # TODO: fetch more if total count > 100
        albums = self.api.user_favorite_albums(user.identifier)
        return [_deserialize(album, _UserAlbumSchema) for album in albums]

    def current_user_fav_create_artists_rd(self):
        user = self.get_current_user()
        if user is None:
            return create_reader([])
        # TODO: fetch more if total count > 100
        mid = self._model_cache_get_or_fetch(user, "mid")
        artists = self.api.user_favorite_artists(user.identifier, mid)
        return [_deserialize(artist, _UserArtistSchema) for artist in artists]

    def current_user_fav_create_playlists_rd(self):
        user = self.get_current_user()
        if user is None:
            return create_reader([])
        mid = self._model_cache_get_or_fetch(user, "mid")
        playlists = self.api.user_favorite_playlists(user.identifier, mid)
        return [_deserialize(playlist, QQPlaylistSchema) for playlist in playlists]

    def has_current_user(self):
        return self._user is not None

    def get_current_user(self):
        return self._user

    def song_list_similar(self, song):
        data_songs = self.api.song_similar(int(song.identifier))
        return [_deserialize(data_song, QQSongSchema) for data_song in data_songs]


def _deserialize(data, schema_cls):
    schema = schema_cls()
    obj = schema.load(data)
    return obj


def create_g(func, identifier, schema):
    data = func(identifier, page=1)
    total = int(data["totalNum"] if schema == _ArtistSongSchema else data["total"])

    def g():
        nonlocal data
        if data is None:
            yield from ()
        else:
            page = 1
            while data["songList"] if schema == _ArtistSongSchema else data["list"]:
                obj_data_list = (
                    data["songList"] if schema == _ArtistSongSchema else data["list"]
                )
                for obj_data in obj_data_list:
                    obj = _deserialize(obj_data, schema)
                    yield obj
                page += 1
                data = func(identifier, page)

    return SequentialReader(g(), total)


def search(keyword, **kwargs):
    type_ = SearchType.parse(kwargs["type_"])
    if type_ == SearchType.pl:
        data = provider.api.search_playlists(keyword)
        playlists = [_deserialize(playlist, _BriefPlaylistSchema) for playlist in data]
        return SimpleSearchResult(q=keyword, playlists=playlists)
    else:
        type_type_map = {
            SearchType.so: 0,
            SearchType.al: 8,
            SearchType.ar: 9,
        }
        data = provider.api.search(keyword, type_=type_type_map[type_])
        if type_ == SearchType.so:
            songs = [_deserialize(song, QQSongSchema) for song in data]
            return SimpleSearchResult(q=keyword, songs=songs)
        elif type_ == SearchType.al:
            albums = [_deserialize(album, _BriefAlbumSchema) for album in data]
            return SimpleSearchResult(q=keyword, albums=albums)
        else:
            artists = [_deserialize(artist, _BriefArtistSchema) for artist in data]
            return SimpleSearchResult(q=keyword, artists=artists)


provider = QQProvider()
provider.search = search


from .schemas import (  # noqa
    QQSongSchema,
    QQArtistSchema,
    _ArtistSongSchema,
    _BriefAlbumSchema,
    _UserArtistSchema,
    _BriefArtistSchema,
    _BriefPlaylistSchema,
    QQAlbumSchema,
    QQPlaylistSchema,
    QQUserSchema,
    _UserAlbumSchema,
)  # noqa
