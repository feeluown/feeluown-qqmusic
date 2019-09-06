from marshmallow import Schema, fields, post_load


class _SongArtistSchema(Schema):
    identifier = fields.Int(load_from='id', required=True)
    name = fields.Str(load_from='name', required=True)

    @post_load
    def create_model(self, data):
        return QQArtistModel(**data)


class _SongAlbumSchema(Schema):
    identifier = fields.Int(load_from='id', required=True)
    name = fields.Str(load_from='name', required=True)

    @post_load
    def create_model(self, data):
        return QQAlbumModel(**data)


class QQSongSchema(Schema):
    identifier = fields.Int(load_from='id', required=True)
    mid = fields.Str(load_from='mid', required=True)
    duration = fields.Float(load_from='interval', required=True)
    title = fields.Str(load_from='name', required=True)
    artists = fields.List(fields.Nested('_SongArtistSchema'), load_from='singer')
    album = fields.Nested('_SongAlbumSchema', required=True)

    files = fields.Dict(load_from='file', missing={})

    @post_load
    def create_model(self, data):
        song = QQSongModel(identifier=data['identifier'],
                           mid=data['mid'],
                           duration=data['duration'] * 1000,
                           title=data['title'],
                           artists=data.get('artists'),
                           album=data.get('album'),)
        return song


class _ArtistSongSchema(Schema):
    value = fields.Nested(QQSongSchema, load_from='musicData')

    @post_load
    def create_model(self, data):
        return data['value']


class _ArtistAlbumSchema(Schema):
    identifier = fields.Int(load_from='albumID', required=True)
    mid = fields.Str(load_from='albumMID', required=True)
    name = fields.Str(load_from='albumName', required=True)

    @post_load
    def create_model(self, data):
        return QQAlbumModel(**data)

class QQArtistSchema(Schema):
    """歌手详情 Schema、歌曲歌手简要信息 Schema"""

    identifier = fields.Int(load_from='singer_id', required=True)
    mid = fields.Str(load_from='singer_mid', required=True)
    name = fields.Str(load_from='singer_name', required=True)

    desc = fields.Str(load_from='SingerDesc')
    songs = fields.List(fields.Nested(_ArtistSongSchema), load_from='list')

    @post_load
    def create_model(self, data):
        return QQArtistModel(**data)


class QQAlbumSchema(Schema):
    album_info = fields.Dict(load_from='getAlbumInfo', required=True)
    album_name = fields.List(fields.Dict(), load_from='getSongInfo', required=True)
    album_desc = fields.Dict(load_from='getAlbumDesc', required=True)
    # 非中文专辑会把专辑的中文翻译加进去, 为保持前后一致此外去掉翻译文字
    artist_info = fields.Dict(load_from='getSingerInfo', required=True)

    # 有的专辑歌曲列表为 null，比如：fuo://qqmusic/albums/8623
    songs = fields.List(fields.Nested(QQSongSchema), load_from='getSongInfo', allow_none=True)

    @post_load
    def create_model(self, data):
        singer_name = data['artist_info']['Fsinger_name']
        artist = QQArtistModel(
            identifier=data['artist_info']['Fsinger_id'],
            # split('/')：有的专辑有个多歌手，只有第一个才是正确的专辑艺人
            # split('(')：有的非中文歌手拥有别名在括号里
            name=singer_name.split('/')[0].split('(')[0].strip())
        album = QQAlbumModel(
            identifier=data['album_info']['Falbum_id'],
            mid=data['album_info']['Falbum_mid'],
            # 非中文专辑会把专辑的中文翻译加进去, 为保持前后一致此外去掉括号里的中文翻译
            name=data['album_name'][0]['album']['name'] or data['album_info']['Falbum_name'],
            desc=data['album_desc']['Falbum_desc'],
            songs=data['songs'] or [],
            artists=[artist])
        return album


from .models import (
    QQSongModel,
    QQArtistModel,
    QQAlbumModel,
)  # noqa
