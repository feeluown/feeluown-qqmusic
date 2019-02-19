import logging
import json

import requests


logger = logging.getLogger(__name__)

api_base_url = 'http://c.y.qq.com'


class API(object):
    """qq music api

    Please http capture request from (mobile) qqmusic mobile web page
    """

    def __init__(self, timeout=1):
        # TODO: 暂时无脑统一一个 timeout
        # 正确的应该是允许不同接口有不同的超时时间
        self._timeout = timeout
        self._headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
            'Referer': 'http://y.qq.com/',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N)'
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/66.0.3359.181 Mobile Safari/537.36',
        }
        self._vkey = None

    @property
    def vkey(self):
        if self._vkey is None:
            self._vkey = self.get_vkey()
        return self._vkey

    def get_cover(self, mid, type_):
        """获取专辑、歌手封面

        :param type_: 专辑： 2，歌手：1
        """
        return 'http://y.gtimg.cn/music/photo_new/T00{}R800x800M000{}.jpg' \
            .format(type_, mid)

    def get_song_detail(self, song_id):
        song_id = int(song_id)
        url = 'http://u.y.qq.com/cgi-bin/musicu.fcg'
        # 往 payload 添加字段，有可能还可以获取相似歌曲、歌单等
        payload = {
            'comm': {
                'g_tk':5381,
                'uin': 0,
                'format': 'json',
                'inCharset': 'utf-8',
                'outCharset': 'utf-8',
                'notice': 0,
                'platform': 'h5',
                'needNewCode': 1
            },
            'detail': {
                'module': 'music.pf_song_detail_svr',
                'method': 'get_song_detail',
                'param': {'song_id': song_id}
            }
        }
        payload_str = json.dumps(payload)
        response = requests.post(url, data=payload_str, headers=self._headers,
                                 timeout=self._timeout)
        data = response.json()
        data_song = data['detail']['data']['track_info']
        if data_song['id'] <= 0:
            return None
        return data_song

    def get_vkey(self):
        url = api_base_url + '/base/fcgi-bin/fcg_music_express_mobile3.fcg'
        # loginUin 和 uin 这两个参数似乎是可有可无的
        # songmid 是随意一个真正可用的 song mid, filename 和 songmid 需要对应
        params = {
            'loginUin': 123456,
            'format': 'json',
            'cid': 205361747,
            'uin': 123456,
            'songmid': '003a1tne1nSz1Y',
            'filename': 'C400003a1tne1nSz1Y.m4a',
            'guid': 10000
        }
        resp = requests.get(url, params=params, headers=self._headers,
                            timeout=2)
        rv = resp.json()
        return rv['data']['items'][0]['vkey']

    def get_song_url(self, song_mid, quality):  # F000(flac) A000(ape) M800(320) C600(192) M500(128)
        if not quality:
            return None
        switcher = {
            'F000': 'flac',
            'A000': 'ape',
            'C600': 'm4a'
        }
        filename = '{}{}.{}'.format(
            quality, song_mid, switcher.get(quality, 'mp3'))
        # song_url = 'http://dl.stream.qqmusic.qq.com/{}?vkey={}&guid={}&uin={}&fromtag={}'.format(
        #     filename, self._vkey, 10000, 123456, 8)
        song_url = 'http://streamoc.music.tc.qq.com/{}?vkey={}&guid={}&uin={}&fromtag={}'.format(
            filename, self.vkey, 10000, 123456, 8)
        return song_url

    def search(self, keyword, limit=20, page=1):
        path = '/soso/fcgi-bin/client_search_cp'
        url = api_base_url + path
        params = {
            # w,n,page are required parameters
            'w': keyword,
            't': 0,  # t=0 代表歌曲，专辑:8, 歌手:9
            'n': limit,
            'page': page,

            # positional parameters
            'cr': 1,  # copyright?

            'new_json': 1,
            'format': 'json',
            'platform': 'yqq.json'
        }
        resp = requests.get(url, params=params, timeout=self._timeout)
        songs = resp.json()['data']['song']['list']
        return songs

    def artist_detail(self, artist_id, page=1, page_size=50):
        """获取歌手详情"""
        path = '/v8/fcg-bin/fcg_v8_singer_track_cp.fcg'
        url = api_base_url + path
        params = {
            'singerid': artist_id,
            'order': 'listen',
            'begin': page - 1,
            'num': page_size,

            # 有 newsong 字段时，服务端会返回含有 file 字段的字典
            'newsong': 1
        }
        resp = requests.get(url, params=params, timeout=self._timeout)
        rv = resp.json()
        return rv['data']

    def artist_albums(self, artist_id, page=1, page_size=20):
        url = api_base_url + '/v8/fcg-bin/fcg_v8_singer_album.fcg'
        params = {
            'singerid': artist_id,
            'order': 'time',
            'begin': page - 1,
            'num': page_size
        }
        response = requests.get(url, params=params)
        js = response.json()
        return js['data']['list']

    def album_detail(self, album_id):
        url = api_base_url + '/v8/fcg-bin/fcg_v8_album_detail_cp.fcg'
        params = {
            'albumid': album_id,
            'format': 'json',
            'newsong': 1
        }
        resp = requests.get(url, params=params)
        return resp.json()['data']
