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
    duration = fields.Float(load_from='interval', required=True)
    title = fields.Str(load_from='name', required=True)
    artists = fields.List(fields.Nested('_SongArtistSchema'), load_from='singer')
    album = fields.Nested('_SongAlbumSchema', required=True)

    files = fields.Dict(load_from='file', missing={})

    @post_load
    def create_model(self, data):
        song = QQSongModel(identifier=data['identifier'],
                           mid=data['files']['media_mid'],
                           duration=data['duration'] * 1000,
                           title=data['title'],
                           artists=data.get('artists'),
                           album=data.get('album'),)
        if data['files'].get('size_320') or data['files'].get('size_320mp3'):
            song.quality = 'M800'
        elif data['files'].get('size_aac') or data['files'].get('size_192aac'):
            song.quality = 'C600'
        elif data['files'].get('size_128') or data['files'].get('size_128mp3'):
            song.quality = 'M500'
        else:
            song.quality = ''
        return song


class _ArtistSongSchema(Schema):
    value = fields.Nested(QQSongSchema, load_from='musicData')


class QQArtistSchema(Schema):
    """歌手详情 Schema、歌曲歌手简要信息 Schema"""

    identifier = fields.Int(load_from='singer_id', required=True)
    mid = fields.Str(load_from='singer_mid', required=True)
    name = fields.Str(load_from='singer_name', required=True)

    desc = fields.Str(load_from='SingerDesc')
    songs = fields.List(fields.Nested(_ArtistSongSchema), load_from='list')

    @post_load
    def create_model(self, data):
        if data['songs']:
            data['songs'] = [song['value'] for song in data['songs']]
        return QQArtistModel(**data)


class QQAlbumSchema(Schema):
    album_desc = fields.Dict(load_from='getAlbumDesc', required=True)
    album_info = fields.Dict(load_from='getAlbumInfo', required=True)

    artist_info = fields.Dict(load_from='getSingerInfo', required=True)

    # 有的专辑歌曲列表为 null，比如：fuo://qqmusic/albums/8623
    songs = fields.List(fields.Nested(QQSongSchema), load_from='getSongInfo', allow_none=True)

    @post_load
    def create_model(self, data):
        singer_name = data['artist_info']['Fsinger_name']
        # split('/')：有的专辑有个多歌手，只有第一个才是正确的专辑艺人
        # split('(')：有的非中文歌手拥有别名在括号里
        singer_name.split('/')[0].split('(')[0].strip()
        artist = QQArtistModel(
            identifier=data['artist_info']['Fsinger_id'],
            name=singer_name)
        album = QQAlbumModel(
            identifier=data['album_info']['Falbum_id'],
            mid=data['album_info']['Falbum_mid'],
            name=data['album_info']['Falbum_name'],
            desc=data['album_desc']['Falbum_desc'],
            songs=data['songs'] or [],
            artists=[artist])
        return album


from .models import (
    QQSongModel,
    QQArtistModel,
    QQAlbumModel,
)  # noqa
