import logging
import json
import random

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

    def get_song_url(self, song_mid):
        songvkey = str(random.random()).replace("0.", "")
        guid = "MS"
        data = {
            "req": {
                "module": "CDN.SrfCdnDispatchServer",
                "method": "GetCdnDispatch",
                "param": {
                    "guid": guid,
                    "calltype": 0,
                    "userip": ""
                }
            },
            "req_0": {
                "module": "vkey.GetVkeyServer",
                "method": "CgiGetVkey",
                "param": {
                    'cid': 205361747,
                    "guid": guid,
                    "songmid": [song_mid],
                    # "filename": [filename],
                    "songtype": [1],
                    "uin": "0",
                    # "loginflag": 1,
                    # "platform": "20"
                }
            },
            "comm": {
                "uin": 0,
                "format": "json",
                "ct": 24,
                "cv": 0
            }
        }
        data_str = json.dumps(data)
        params = {
            '-': 'getplaysongvkey' + str(songvkey),
            'g_tk': 5381,
            'loginUin': 0,
            'hostUin': 0,
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf8',
            'notice': 0,
            'platform': 'yqq.json',
            'needNewCode': 0,
        }
        # 这里没有把 data=data_str 放在 params 中，因为 QQ 服务端不识别这种写法
        # 另外测试发现：python(flask) 是可以识别这两种写法的
        url = 'http://u.y.qq.com/cgi-bin/musicu.fcg?data=' + data_str
        resp = requests.get(url, params=params, headers=self._headers)
        js = resp.json()
        midurlinfo = js['req_0']['data']['midurlinfo']
        if midurlinfo:
            purl = midurlinfo[0]['purl']
            prefix = 'http://dl.stream.qqmusic.qq.com/'
            valid_url = ''
            # 有部分音乐网页版接口中没有，比如 晴天-周杰伦，
            # 但是通过下面的黑魔法是可以获取的
            quality_suffix = [
                ('M500', 'mp3'),
                # 经过个人(cosven)测试，M500 品质的成功率非常高
                # 而下面三个从来不会成功，所以不尝试下面三个
                # ('F000', 'flac'),
                # ('A000', 'ape'),
                # ('M800', 'mp3'),
            ]
            C400_filename = midurlinfo[0]['filename']
            pure_filename = C400_filename[4:-3]
            vkey = js['req']['data']['vkey']
            for q, s in quality_suffix:
                q_filename = q + pure_filename + s
                url = '{}{}?vkey={}&guid=MS&uin=0&fromtag=8'\
                    .format(prefix, q_filename, vkey)
                _resp = requests.head(url, headers=self._headers)
                if _resp.status_code == 200:
                    valid_url = url
                    logger.info('song:{} quality:{} url is valid'.format(song_mid, q))
                    break
                logger.info('song:{} quality:{} url is invalid'.format(song_mid, q))
            # 尝试拿到网页版接口的 url
            if not valid_url and purl:
                song_path = purl
                valid_url = prefix + song_path
                logger.info('song:{} quality:web url is valid'.format(song_mid))
            return valid_url
        return ''

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
        return js['data']

    def album_detail(self, album_id):
        url = api_base_url + '/v8/fcg-bin/fcg_v8_album_detail_cp.fcg'
        params = {
            'albumid': album_id,
            'format': 'json',
            'newsong': 1
        }
        resp = requests.get(url, params=params)
        return resp.json()['data']
