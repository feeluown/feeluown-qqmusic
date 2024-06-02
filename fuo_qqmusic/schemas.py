import logging

from marshmallow import Schema, fields, post_load, EXCLUDE
from feeluown.library import (
    SongModel,
    BriefAlbumModel,
    BriefArtistModel,
    ArtistModel,
    AlbumModel,
    PlaylistModel,
    BriefPlaylistModel,
    UserModel,
    VideoModel,
)

logger = logging.getLogger(__name__)


class BaseSchema(Schema):
    source = fields.Str(missing="qqmusic")

    class Meta:
        unknown = EXCLUDE


SOURCE = "qqmusic"
Schema = BaseSchema


def get_cover(mid, type_):
    """获取专辑、歌手封面

    :param type_: 专辑： 2，歌手：1
    """
    return f'http://y.gtimg.cn/music/photo_new/T00{type_}R800x800M000{mid}.jpg'


def create_model(model_cls, data, fields_to_cache=None):
    """
    maybe this function should be provided by feeluown

    :param fields_to_cache: list of fields name to be cached
    """
    if fields_to_cache is not None:
        cache_data = {}
        for field in fields_to_cache:
            value = data.pop(field)
            if value is not None:
                cache_data[field] = value
        model = model_cls(**data)
        for field, value in cache_data.items():
            model.cache_set(field, value)
    else:
        model = model_cls(**data)
    return model


def pop_album_from_data(data):
    album_id = data.pop("albumid")
    album_mid = data.pop("albummid")
    album_name = data.pop("albumname")
    album_data = {
        "identifier": album_id,
        "source": SOURCE,
        "mid": album_mid,
        "name": album_name,
    }
    return create_model(BriefAlbumModel, album_data, ["mid"])


class _SongArtistSchema(Schema):
    identifier = fields.Int(data_key="id", required=True)
    name = fields.Str(data_key="name", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return BriefArtistModel(**data)


class _SongAlbumSchema(Schema):
    identifier = fields.Int(data_key="id", required=True)
    name = fields.Str(data_key="name", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return BriefAlbumModel(**data)


class QQSongSchema(Schema):
    identifier = fields.Int(data_key="id", required=True)
    mid = fields.Str(data_key="mid", required=True)
    duration = fields.Float(data_key="interval", required=True)
    title = fields.Str(data_key="title", required=True)
    artists = fields.List(fields.Nested("_SongArtistSchema"), data_key="singer")
    album = fields.Nested("_SongAlbumSchema", required=True)
    files = fields.Dict(data_key="file", missing={})
    mv = fields.Dict(required=True)

    @post_load
    def create_model(self, data, **kwargs):
        song = SongModel(
            identifier=data["identifier"],
            source=SOURCE,
            duration=data["duration"] * 1000,
            title=data["title"],
            artists=data.get("artists", []),
            album=data["album"],
        )
        song.cache_set("mid", data["mid"])
        song.cache_set("media_id", data["files"]["media_mid"])
        song.cache_set("mv_id", data["mv"].get("vid", 0))
        # 记录有哪些资源文件, 没有权限的用户依然获取不到
        quality_suffix = []
        files = data["files"]
        if files.get("size_flac"):  # has key and value is not empty
            quality_suffix.append(("shq", "F000", 800, "flac"))
        elif files.get("size_ape"):
            quality_suffix.append(("shq", "A000", 800, "ape"))
        if files.get("size_320") or files.get("size_320mp3"):
            quality_suffix.append(("hq", "M800", 320, "ape"))
        if files.get("size_aac") or files.get("size_192aac"):
            quality_suffix.append(("sq", "C600", 192, "m4a"))
        if files.get("size_128") or files.get("size_128mp3"):
            quality_suffix.append(("lq", "M500", 128, "mp3"))
        song.cache_set("quality_suffix", quality_suffix)
        return song


class _ArtistSongSchema(Schema):
    value = fields.Nested(QQSongSchema, data_key="songInfo")

    @post_load
    def create_model(self, data, **kwargs):
        return data["value"]


class _BriefArtistSchema(Schema):
    identifier = fields.Int(data_key="singerID", required=True)
    mid = fields.Str(data_key="singerMID", required=True)
    name = fields.Str(data_key="singerName", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return create_model(BriefArtistModel, data, ["mid"])


class SearchArtistSchema(_BriefArtistSchema):
    pic_url = fields.Str(data_key="singerPic", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        data['hot_songs'] = []
        data['description'] = ''
        data['aliases'] = []
        return create_model(ArtistModel, data, ["mid"])


class _BriefAlbumSchema(Schema):
    identifier = fields.Int(data_key="albumID", required=True)
    mid = fields.Str(data_key="albumMID", required=True)
    name = fields.Str(data_key="albumName", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return create_model(BriefAlbumModel, data, ["mid"])


class SearchAlbumSchema(_BriefAlbumSchema):
    cover = fields.Str(data_key="albumPic", required=True)
    released = fields.Str(data_key="publicTime", required=True)
    song_count = fields.Int(required=True)
    artists = fields.List(fields.Nested(_SongArtistSchema),
                          data_key="singer_list",
                          required=True)
    @post_load
    def create_model(self, data, **kwargs):
        data['description'] = ''
        data['songs'] = []
        return create_model(AlbumModel, data, ['mid'])


class _BriefPlaylistSchema(Schema):
    identifier = fields.Int(data_key="dissid", required=True)
    name = fields.Str(data_key="dissname", required=True)
    cover = fields.Str(data_key="imgurl", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        data['description'] = ''
        return create_model(PlaylistModel, **data)


class PlaylistUserSchema(Schema):
    identifier = fields.Str(data_key="creator_uin", required=True)
    mid = fields.Str(data_key="encrypt_uin", required=True)
    name = fields.Str(required=True)
    avatar_url = fields.Str(required=True, data_key="avatarUrl")

    @post_load
    def create_model(self, data, **kwargs):
        return create_model(UserModel, data, ['mid'])


class SearchPlaylistSchema(_BriefPlaylistSchema):
    creator = fields.Nested("PlaylistUserSchema", required=True)
    description = fields.Str(data_key="introduction", required=True)
    play_count = fields.Int(data_key="listennum", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return create_model(PlaylistModel, data)


class QQArtistSchema(Schema):
    """歌手详情 Schema、歌曲歌手简要信息 Schema"""

    identifier = fields.Int(data_key="singer_id", required=True)
    mid = fields.Str(data_key="singer_mid", required=True)
    name = fields.Str(data_key="singer_name", required=True)

    description = fields.Str(data_key="SingerDesc", missing="")
    hot_songs = fields.List(
        fields.Nested(_ArtistSongSchema), data_key="list", missing=list
    )

    @post_load
    def create_model(self, data, **kwargs):
        data["pic_url"] = get_cover(data['mid'], 1)
        data["aliases"] = []
        return create_model(ArtistModel, data, ["mid"])


class QQAlbumSchema(Schema):
    album_info = fields.Dict(data_key="getAlbumInfo", required=True)
    album_desc = fields.Dict(data_key="getAlbumDesc", required=True)
    # 非中文专辑会把专辑的中文翻译加进去, 为保持前后一致此外去掉翻译文字
    artist_info = fields.Dict(data_key="getSingerInfo", required=True)

    # 有的专辑歌曲列表为 null，比如：fuo://qqmusic/albums/8623
    songs = fields.List(
        fields.Nested(QQSongSchema), data_key="getSongInfo", allow_none=True
    )

    @post_load
    def create_model(self, data, **kwargs):
        singer_name = data["artist_info"]["Fsinger_name"]
        artist = BriefArtistModel(
            identifier=data["artist_info"]["Fsinger_id"],
            source=SOURCE,
            # split('/')：有的专辑有个多歌手，只有第一个才是正确的专辑艺人
            # split('(')：有的非中文歌手拥有别名在括号里
            name=singer_name.split("/")[0].split("(")[0].strip(),
        )
        # 非中文专辑会把专辑的中文翻译加进去, 为保持前后一致此外去掉括号里的中文翻译
        if data["songs"]:
            album_name = data["songs"][0].album.name
        else:
            album_name = data["album_info"]["Falbum_name"]
        mid = data["album_info"]["Falbum_mid"]
        album = AlbumModel(
            identifier=data["album_info"]["Falbum_id"],
            source=SOURCE,
            name=album_name,
            description=data["album_desc"]["Falbum_desc"],
            songs=data["songs"] or [],
            artists=[artist],
            cover=get_cover(mid, 2)
        )
        album.cache_set("mid", mid)
        return album


class QQPlaylistSchema(Schema):
    identifier = fields.Int(required=True, data_key="dissid")
    name = fields.Str(required=True, data_key="dissname")
    cover = fields.Str(required=True, data_key="logo")
    # songs field maybe null, though it can't be null in model
    songs = fields.List(
        fields.Nested(QQSongSchema), data_key="songlist", allow_none=True
    )

    @post_load
    def create_model(self, data, **kwargs):
        fields_to_cache = []
        if data.get('songs') is not None:
            fields_to_cache = ['songs']
        data['description'] = ''
        return create_model(PlaylistModel, data, fields_to_cache)


class _UserArtistSchema(Schema):
    other_infos = fields.Dict(data_key="OtherInfo", required=True)
    mid = fields.Str(data_key="MID", required=True)
    name = fields.Str(data_key="Name", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        data["identifier"] = data.pop("other_infos")["SingerID"]
        return create_model(BriefArtistModel, data, ['mid'])


class _UserAlbumSchema(Schema):
    identifier = fields.Int(data_key="albumid", required=True)
    mid = fields.Str(data_key="albummid", required=True)
    name = fields.Str(data_key="albumname", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return create_model(BriefAlbumModel, data, ["mid"])


class _UserPlaylistSchema(Schema):
    identifier = fields.Int(data_key="dissid", required=True)
    name = fields.Str(data_key="title", required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return create_model(BriefPlaylistModel, data)


class QQUserSchema(Schema):
    creator = fields.Dict(required=True)
    mydiss = fields.Dict(required=True)

    @post_load
    def create_model(self, data, **kwargs):
        creator = data["creator"]
        playlists_data = data["mydiss"]["list"]
        schema = _UserPlaylistSchema()
        playlists = []
        for each in playlists_data:
            playlist = schema.load(each)
            playlists.append(playlist)
        data = dict(
            identifier=creator["uin"],
            source=SOURCE,
            mid=creator["encrypt_uin"],
            name=creator["nick"],
            fav_pid=creator["fav_pid"],
            avatar_url=creator["headpic"],
            playlists=playlists,
        )
        return create_model(UserModel, data, ['mid', 'fav_pid', 'playlists'])


class SearchMVSchema(Schema):
    # 使用 mv_id 字段的话，目前拿不到播放 url，用 v_id  比较合适
    identifier = fields.Str(data_key="v_id", required=True)
    title = fields.Str(data_key="mv_name", required=True)
    artists = fields.List(fields.Nested("_SongArtistSchema"),
                          data_key="singer_list",
                          required=True)
    duration = fields.Int(required=True)
    cover = fields.Str(data_key="mv_pic_url", required=True)
    play_count = fields.Int(required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return create_model(VideoModel, data)
