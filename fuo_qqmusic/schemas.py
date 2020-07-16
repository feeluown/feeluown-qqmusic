

from marshmallow import Schema, fields, post_load, EXCLUDE
import logging
logger = logging.getLogger(__name__)


class BaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE


Schema = BaseSchema


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


class QQMvUrlSchema(Schema):
    freeflow_url = fields.List(fields.Str(
        required=True), ata_key='freeflow_url')
    file_type = fields.Int(data_key='filetype', required=True)


class QQMvSchema(Schema):
    url = fields.List(fields.Nested(QQMvUrlSchema),
                      data_key='mp4', required=True)

    @post_load
    def create_model(self, data, **kwargs):

        url = data['url']

        fhd = hd = sd = ld = None
        for item in url:
            # print("item",item)
            if item['file_type'] == 40:
                if (item['freeflow_url']):
                    fhd = item['freeflow_url'][0]
            elif item['file_type'] == 30:
                if (item['freeflow_url']):
                    hd = item['freeflow_url'][0]
            elif item['file_type'] == 20:
                if (item['freeflow_url']):
                    sd = item['freeflow_url'][0]
            elif item['file_type'] == 10:
                if (item['freeflow_url']):
                    ld = item['freeflow_url'][0]
            elif item['file_type'] == 0:
                pass
            else:
                logger.warning(
                    'There exists another quality:%s mv.', item['file_type'])
        data['q_url_mapping'] = dict(fhd=fhd, hd=hd, sd=sd, ld=ld)
        return QQMvModel(**data)


class QQSongSchema(Schema):
    identifier = fields.Int(data_key='songid', required=True)
    mid = fields.Str(data_key='songmid', required=True)
    duration = fields.Float(data_key='interval', required=True)
    title = fields.Str(data_key='songname', required=True)
    artists = fields.List(fields.Nested('_SongArtistSchema'),
                          data_key='singer')

    @post_load
    def create_model(self, data, **kwargs):
        song = QQSongModel(identifier=data['identifier'],
                           mid=data['mid'],
                           duration=data['duration'] * 1000,
                           title=data['title'],
                           artists=data.get('artists'),
                           album=data.get('album'),)
        return song


class QQSongDetailSchema(Schema):
    identifier = fields.Int(data_key='id', required=True)
    mid = fields.Str(data_key='mid', required=True)
    duration = fields.Float(data_key='interval', required=True)
    title = fields.Str(data_key='name', required=True)
    artists = fields.List(fields.Nested('_SongArtistSchema'),
                          data_key='singer')
    album = fields.Nested('_SongAlbumSchema', required=True, data_key='album')

    files = fields.Dict(data_key='file', missing={})

    @post_load
    def create_model(self, data, **kwargs):
        song = QQSongModel(identifier=data['identifier'],
                           mid=data['mid'],
                           duration=data['duration'] * 1000,
                           title=data['title'],
                           artists=data.get('artists'),
                           album=data.get('album'),)
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


class QQUserAlbumSchema(Schema):
    identifier = fields.Int(required=True, data_key='albumid')
    mid = fields.Str(required=True, data_key='albummid')
    name = fields.Str(required=True, data_key='albumname')
    cover = fields.Url(required=True, data_key='pic')

    @post_load
    def create_model(self, data, **kwargs):
        # if data.get('desc') is None:
        #     data['desc'] = ''
        return QQUserAlbumModel(**data)


class QQPlaylistSchema(Schema):
    identifier = fields.Int(required=True, data_key='disstid')
    dirid = fields.Int(required=True, data_key='dirid')
    name = fields.Str(required=True, data_key='dissname')
    cover = fields.Url(required=True, data_key='logo')
    # songs field maybe null, though it can't be null in model
    songs = fields.List(fields.Nested(QQSongSchema),
                        data_key='songlist',
                        allow_none=True)

    @post_load
    def create_model(self, data, **kwargs):
        # if data.get('desc') is None:
        #     data['desc'] = ''
        return QQPlaylistModel(**data)


class QQUserSchema(Schema):

    name = fields.Str(required=True)
    playlists = fields.List(fields.Nested(QQPlaylistSchema))
    fav_playlists = fields.List(fields.Nested(QQPlaylistSchema))

    @post_load
    def create_model(self, data, **kwargs):
        return QQUserModel(**data)


from .models import (  # noqa
    QQUserAlbumModel,
    QQMvModel,
    QQSongModel,
    QQArtistModel,
    QQAlbumModel,
    QQUserModel,
    QQPlaylistModel,
)
