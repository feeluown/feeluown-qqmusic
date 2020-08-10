

from marshmallow import Schema, fields, post_load, EXCLUDE
import logging
logger = logging.getLogger(__name__)


class BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE


Schema = BaseSchema


def pop_album_from_data(data):
    album_id = data.pop('albumid')
    album_mid = data.pop('albummid')
    album_name = data.pop('albumname')
    album_data = {
        'identifier': album_id,
        'mid': album_mid,
        'name': album_name,
    }
    return QQAlbumModel(**album_data)


class _SongArtistSchema(Schema):
    identifier = fields.Int(data_key='id', required=True)
    name = fields.Str(data_key='name', required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return QQArtistModel(**data)


class _SongAlbumSchema(Schema):
    identifier = fields.Int(data_key='id', required=True)
    name = fields.Str(data_key='name', required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return QQAlbumModel(**data)


class QQSongSchema(Schema):
    identifier = fields.Int(data_key='id', required=True)
    mid = fields.Str(data_key='mid', required=True)
    duration = fields.Float(data_key='interval', required=True)
    title = fields.Str(data_key='name', required=True)
    artists = fields.List(fields.Nested('_SongArtistSchema'),
                          data_key='singer')
    album = fields.Nested('_SongAlbumSchema', required=True)
    files = fields.Dict(data_key='file', missing={})
    mv = fields.Dict(required=True)

    @post_load
    def create_model(self, data, **kwargs):
        song = QQSongModel(identifier=data['identifier'],
                           mid=data['mid'],
                           duration=data['duration'] * 1000,
                           title=data['title'],
                           artists=data.get('artists'),
                           album=data.get('album'),
                           mvid=data['mv'].get('vid', 0))
        return song


class _ArtistSongSchema(Schema):
    value = fields.Nested(QQSongSchema, data_key='musicData')

    @post_load
    def create_model(self, data, **kwargs):
        return data['value']


class _ArtistAlbumSchema(Schema):
    identifier = fields.Int(data_key='albumID', required=True)
    mid = fields.Str(data_key='albumMID', required=True)
    name = fields.Str(data_key='albumName', required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return QQAlbumModel(**data)


class QQArtistSchema(Schema):
    """歌手详情 Schema、歌曲歌手简要信息 Schema"""

    identifier = fields.Int(data_key='singer_id', required=True)
    mid = fields.Str(data_key='singer_mid', required=True)
    name = fields.Str(data_key='singer_name', required=True)

    desc = fields.Str(data_key='SingerDesc')
    songs = fields.List(fields.Nested(_ArtistSongSchema), data_key='list')

    @post_load
    def create_model(self, data, **kwargs):
        return QQArtistModel(**data)


class QQAlbumSchema(Schema):
    album_info = fields.Dict(data_key='getAlbumInfo', required=True)
    album_desc = fields.Dict(data_key='getAlbumDesc', required=True)
    # 非中文专辑会把专辑的中文翻译加进去, 为保持前后一致此外去掉翻译文字
    artist_info = fields.Dict(data_key='getSingerInfo', required=True)

    # 有的专辑歌曲列表为 null，比如：fuo://qqmusic/albums/8623
    songs = fields.List(fields.Nested(QQSongSchema),
                        data_key='getSongInfo', allow_none=True)

    @post_load
    def create_model(self, data, **kwargs):
        singer_name = data['artist_info']['Fsinger_name']
        artist = QQArtistModel(
            identifier=data['artist_info']['Fsinger_id'],
            # split('/')：有的专辑有个多歌手，只有第一个才是正确的专辑艺人
            # split('(')：有的非中文歌手拥有别名在括号里
            name=singer_name.split('/')[0].split('(')[0].strip())
        # 非中文专辑会把专辑的中文翻译加进去, 为保持前后一致此外去掉括号里的中文翻译
        if data['songs']:
            # FIXME: this is dangerous since this may trigger web request
            album_name = data['songs'][0].album.name
        else:
            album_name = data['album_info']['Falbum_name'],
        album = QQAlbumModel(
            identifier=data['album_info']['Falbum_id'],
            mid=data['album_info']['Falbum_mid'],
            name=album_name,
            desc=data['album_desc']['Falbum_desc'],
            songs=data['songs'] or [],
            artists=[artist])
        return album


class _PlaylistSongSchema(Schema):
    """SongSchema for song in a playlist"""
    identifier = fields.Int(data_key='songid', required=True)
    mid = fields.Str(data_key='songmid', required=True)
    duration = fields.Float(data_key='interval', required=True)
    title = fields.Str(data_key='songname', required=True)
    artists = fields.List(fields.Nested('_SongArtistSchema'),
                          data_key='singer')
    albumid = fields.Int(data_key='albumid', required=True)
    albummid = fields.Str(data_key='albummid', required=True)
    albumname = fields.Str(data_key='albumname', required=True)

    @post_load
    def create_model(self, data, **kwargs):
        data['duration'] = data['duration'] * 1000
        album = pop_album_from_data(data)
        song = QQSongModel(album=album, **data)
        return song


class QQPlaylistSchema(Schema):
    identifier = fields.Int(required=True, data_key='disstid')
    name = fields.Str(required=True, data_key='dissname')
    cover = fields.Url(required=True, data_key='logo')
    # songs field maybe null, though it can't be null in model
    songs = fields.List(fields.Nested(_PlaylistSongSchema),
                        data_key='songlist',
                        allow_none=True)

    @post_load
    def create_model(self, data, **kwargs):
        return QQPlaylistModel(**data)


class _UserPlaylistSchema(Schema):
    identifier = fields.Int(data_key='dissid', required=True)
    name = fields.Str(data_key='title', required=True)

    @post_load
    def create_model(self, data, **kwargs):
        return QQPlaylistModel(**data)


class QQUserSchema(Schema):
    creator = fields.Dict(required=True)
    mydiss = fields.Dict(required=True)

    @post_load
    def create_model(self, data, **kwargs):
        creator = data['creator']
        playlists_data = data['mydiss']['list']
        schema = _UserPlaylistSchema()
        playlists = []
        for each in playlists_data:
            playlist = schema.load(each)
            playlists.append(playlist)
        return QQUserModel(identifier=creator['uin'],
                           name=creator['nick'],
                           playlists=playlists)


from .models import (  # noqa
    QQSongModel,
    QQArtistModel,
    QQAlbumModel,
    QQUserModel,
    QQPlaylistModel,
)
