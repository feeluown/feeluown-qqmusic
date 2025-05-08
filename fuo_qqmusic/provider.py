import logging
from typing import List, Optional, Protocol, Tuple
from feeluown.excs import ModelNotFound
from feeluown.library import (
    AbstractProvider,
    BriefSongModel,
    PlaylistModel,
    Collection,
    CollectionType,
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
    SupportsAlbumSongsReader,
    SupportsArtistGet,
    SupportsPlaylistGet,
    SupportsPlaylistSongsReader,
    SupportsRecACollectionOfSongs,
    SimpleSearchResult,
    SearchType,
    ModelType,
    UserModel,
)
from feeluown.media import Media, Quality
from feeluown.utils.reader import create_reader, SequentialReader
from .api import API
from .login import read_cookies
from .excs import QQIOError


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
    SupportsRecACollectionOfSongs,
    SupportsAlbumSongsReader,
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

    def auto_login(self):
        cookies = read_cookies()
        user, err = self.try_get_user_from_cookies(cookies)
        if user:
            self.auth(user)
        else:
            logger.info(f'Auto login failed: {err}')

    def try_get_user_from_cookies(self, cookies) -> Tuple[Optional[UserModel], str]:
        if not cookies:  # is None or empty
            return None, 'empty cookies'

        uin = provider.api.get_uin_from_cookies(cookies)
        if uin is None:
            return None, "can't extract user info from cookies"

        provider.api.set_cookies(cookies)
        # try to extract current user
        try:
            user = provider.user_get(uin)
        except QQIOError:
            provider.api.set_cookies(None)
            return None, 'get user info with cookies failed, expired cookies?'
        return user, ''

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
        quality_suffix = self._model_cache_get_or_fetch(song, "quality_suffix")
        mid = self._model_cache_get_or_fetch(song, "mid")
        media_id = self._model_cache_get_or_fetch(song, "media_id")
        media = q_media_mapping.get(quality)
        if media is UNFETCHED_MEDIA:
            for q, t, b, s in quality_suffix:
                if quality == Quality.Audio(q):
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

    def album_create_songs_rd(self, album):
        album = self.album_get(album.identifier)
        return create_reader(album.songs)

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

    def __rec_hot_playlists(self):
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

    def rec_list_daily_songs(self):
        # TODO: cache API result
        feed = self.api.get_recommend_feed()
        card = None
        for shelf_ in feed['v_shelf']:
            if 'moduleID' not in shelf_['extra_info']:
                for batch in shelf_['v_niche']:
                    for card in batch['v_card']:
                        if (
                            card['extra_info'].get('moduleID', '').startswith('recforyou')
                            and card['jumptype'] == 10014  # 10014->playlist
                        ):
                            card = card
                            break
        if card is None:
            logger.warning("No daily songs found")
            return []
        playlist_id = card['id']
        playlist = self.playlist_get(playlist_id)
        return self.playlist_create_songs_rd(playlist).readall()

    def rec_list_daily_playlists(self):
        # TODO: cache API result
        feed = self.api.get_recommend_feed()
        shelf = None
        for shelf_ in feed['v_shelf']:
            # I guess 10046 means 'song'.
            if shelf_['extra_info'].get('moduleID', '').startswith('playlist'):
                shelf = shelf_
                break
        if shelf is None:
            return []
        playlists = []
        for batch in shelf['v_niche']:
            for card in batch['v_card']:
                if card['jumptype'] == 10014:  # 10014->playlist
                    playlists.append(
                        PlaylistModel(identifier=str(card['id']),
                                      source=SOURCE,
                                      name=card['title'],
                                      cover=card['cover'],
                                      description=card['miscellany']['rcmdtemplate'],
                                      play_count=card['cnt'])
                    )
        return playlists

    def rec_a_collection_of_songs(self):
        # TODO: cache API result
        feed = self.api.get_recommend_feed()
        shelf = None
        for shelf_ in feed['v_shelf']:
            # I guess 10046 means 'song'.
            if int(shelf_['miscellany'].get('jumptype', 0)) == 10046:
                shelf = shelf_
                break
        if shelf is None:
            return Collection(name='',
                              type_=CollectionType.only_songs,
                              models=[],
                              description='')
        title = shelf['title_content'] or shelf['title_template']
        song_ids = []
        for batch in shelf['v_niche']:
            for card in batch['v_card']:
                if card['jumptype'] == 10046:
                    song_id = int(card['id'])
                    if song_id not in song_ids:
                        song_ids.append(song_id)

        tracks = self.api.batch_song_details(song_ids)
        return Collection(name=title,
                          type_=CollectionType.only_songs,
                          models=[_deserialize(track, QQSongSchema) for track in tracks],
                          description='')

    def current_user_get_radio_songs(self):
        songs_data = self.api.get_radio_music()
        return [_deserialize(s, QQSongSchema) for s in songs_data]

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
    type_type_map = {
        SearchType.so: 0,
        SearchType.ar: 1,
        SearchType.al: 2,
        SearchType.pl: 3,
        SearchType.vi: 4,
    }
    data = provider.api.search(keyword, type_=type_type_map[type_])
    if type_ == SearchType.so:
        songs = [_deserialize(song, QQSongSchema) for song in data]
        return SimpleSearchResult(q=keyword, songs=songs)
    if type_ == SearchType.ar:
        artists = [_deserialize(artist, SearchArtistSchema) for artist in data]
        return SimpleSearchResult(q=keyword, artists=artists)
    elif type_ == SearchType.al:
        albums = [_deserialize(album, SearchAlbumSchema) for album in data]
        return SimpleSearchResult(q=keyword, albums=albums)
    elif type_ == SearchType.pl:
        playlists = [_deserialize(playlist, SearchPlaylistSchema) for playlist in data]
        return SimpleSearchResult(q=keyword, playlists=playlists)
    elif type_ == SearchType.vi:
        models = [_deserialize(model, SearchMVSchema) for model in data]
        return SimpleSearchResult(q=keyword, videos=models)


provider = QQProvider()
provider.search = search


from .schemas import (  # noqa
    QQSongSchema,
    QQArtistSchema,
    _ArtistSongSchema,
    _BriefAlbumSchema,
    _UserArtistSchema,
    _BriefArtistSchema,
    QQAlbumSchema,
    QQPlaylistSchema,
    QQUserSchema,
    _UserAlbumSchema,
    SearchAlbumSchema,
    SearchArtistSchema,
    SearchPlaylistSchema,
    SearchMVSchema,
)  # noqa
