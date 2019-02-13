import logging
import re

from fuocore.models import (
    BaseModel,
    SongModel,
    PlaylistModel,
    AlbumModel,
    ArtistModel,
    SearchModel,
    ModelStage,
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


def _deserialize(data, schema_cls):
    schema = schema_cls(strict=True)
    obj, _ = schema.load(data)
    # XXX: 将 model 设置为 gotten，减少代码编写时的心智负担，
    # 避免在调用 get 方法时进入无限递归。
    obj.stage = ModelStage.gotten
    return obj


class QQSongModel(SongModel, QQBaseModel):

    @classmethod
    def get(cls, identifier):
        data = cls._api.get_song_detail(identifier)
        song = _deserialize(data, QQSongSchema)
        return song

    @property
    def url(self):
        if self._url is not None:
            return self._url
        url = self._api.get_song_url(self.mid, self.quality)
        if url is not None:
            self._url = url
        else:
            self._url = ''
        return self._url

    @url.setter
    def url(self, url):
        self._url = url


class QQAlbumModel(AlbumModel, QQBaseModel):
    @classmethod
    def get(cls, identifier):
        data_album = cls._api.album_detail(identifier)
        album = _deserialize(data_album, QQAlbumSchema)
        album.cover = cls._api.get_cover(album.mid, 2)
        return album

    def _more_info(self):
        data = self._api.album_detail(self.identifier)
        if data is None:
            return {}

        fil = re.compile(u'[^0-9a-zA-Z/&]+', re.UNICODE)
        tag_info = {
            'albumartist': self.artists_name,
            'date': data['getAlbumInfo']['Fpublic_time'] + 'T00:00:00',
            'genre': (fil.sub(' ', data['genre'])).strip()}

        try:
            songs_identifier = [int(song['id']) for song in data['getSongInfo']]
            songs_disc = [song['index_cd'] + 1 for song in data['getSongInfo']]
            disc_counts = {x: songs_disc.count(x) for x in range(1, max(songs_disc) + 1)}
            track_bias = [0]
            for i in range(1, len(disc_counts)):
                track_bias.append(track_bias[-1] + disc_counts[i])
            tag_info['discs'] = dict(zip(songs_identifier, [str(disc) + '/' + str(songs_disc[-1])
                                                            for disc in songs_disc]))
            tag_info['tracks'] = dict(zip(songs_identifier, [
                str(song['index_album'] - track_bias[song['index_cd']]) + '/' + str(disc_counts[song['index_cd'] + 1])
                for song in data['getSongInfo']]))
        except Exception as e:
            logger.error(e)
        return tag_info


class QQArtistModel(ArtistModel, QQBaseModel):
    @classmethod
    def get(cls, identifier):
        data_artist = cls._api.artist_detail(identifier)
        artist = _deserialize(data_artist, QQArtistSchema)
        artist.cover = cls._api.get_cover(artist.mid, 1)
        return artist

    # @property
    # def albums(self):
    #     if self._albums is None:
    #         self._albums = []
    #         data_albums = self._api.artist_albums(self.identifier) or []
    #         if data_albums:
    #             for data_album in data_albums:
    #                 data = {
    #                     'id': data_album['albumID'],
    #                     'mid': data_album['albumMID'],
    #                     'name': data_album['albumName'],
    #                     'desc': '',
    #                     'singerid': data_album['singerID'],
    #                     'singername': data_album['singerName'],
    #                     'list': []
    #                 }
    #                 album = _deserialize(data, QQAlbumSchema)
    #                 album.cover = self._api.get_cover(album.mid, 2)
    #                 album.songs = None
    #                 album.stage = ModelStage.inited
    #                 self._albums.append(album)
    #     return self._albums
    #
    # @albums.setter
    # def albums(self, value):
    #     self._albums = value


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
)  # noqa
