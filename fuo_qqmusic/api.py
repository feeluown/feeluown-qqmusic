#!/usr/bin/env python
# encoding: UTF-8

import base64
import re
import hashlib
import logging
import math
import json
import random
import time

import requests
from .excs import QQIOError

logger = logging.getLogger(__name__)


def djb2(string):
    ''' Hash a word using the djb2 algorithm with the specified base. '''
    h = 5381
    for c in string:
        h = ((h << 5) + h + ord(c)) & 0xffffffff
    return str(2147483647 & h)


# reference from: https://blog.csdn.net/zq1391345114/article/details/113815906
def _get_sign(data):
    # zza+一段随机的小写字符串，由小写字母和数字组成，长度为10-16位+CJBPACrRuNy7和data取md5。
    st = 'abcdefghijklmnopqrstuvwxyz0123456789'
    count = (math.floor(random.randint(10, 16)))
    sign = 'zza'
    for i in range(count):
        sign += st[math.floor(random.randint(0, 35))]
    s = 'CJBPACrRuNy7' + data
    s_md5 = hashlib.md5(s.encode('utf-8')).hexdigest()
    sign += s_md5
    return sign


class CodeShouldBe0(QQIOError):
    def __init__(self, data):
        self._code = data['code']

    def __str__(self):
        return f'json code field should be 0, got {self._code}'

    @classmethod
    def check(cls, data):
        if data['code'] != 0:
            raise cls(data)


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
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0;'
                          ' Nexus 5 Build/MRA58N)'
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/66.0.3359.181 Mobile Safari/537.36',
        }
        self.set_cookies(None)

    def set_cookies(self, cookies):
        """

        :type cookies: dict
        """
        if cookies:
            self._cookies = cookies
            self._uin = self.get_uin_from_cookies(cookies)
            self._guid = cookies.get('guid', str(int(random.random() * 1000000000)))
        else:
            self._cookies = None
            self._uin = '0'
            self._guid = str(int(random.random() * 1000000000))  # 暂时不知道 guid 有什么用

    def get_uin_from_cookies(self, cookies):
        if 'wxuin' in cookies:
            # a sample wxuin: o1152921504803324670
            # remove the 'o' prefix
            wxuin = cookies['wxuin']
            if wxuin.startswith('o'):
                uin = wxuin[1:]
            else:
                uin = wxuin
        else:
            uin = cookies.get('uin')
        return uin

    def get_token_from_cookies(self):
        cookies = self._cookies
        if not cookies:
            return 5381  # 不知道这个数字有木有特殊含义

        # 不同客户端cookies返回的字段类型各有不同, 这里做一个折衷
        string = cookies.get('qqmusic_key') or cookies.get('p_skey') or \
            cookies.get('skey') or cookies.get('p_lskey') or \
            cookies.get('lskey') or ''
        return djb2(string)

    def get_cover(self, mid, type_):
        """获取专辑、歌手封面

        :param type_: 专辑： 2，歌手：1
        """
        return 'http://y.gtimg.cn/music/photo_new/T00{}R800x800M000{}.jpg' \
            .format(type_, mid)

    def search(self, keyword, type_=0, limit=20, page=1):
        # Other supported types: songlist, user, mv, qc, gedantip, zhida.
        if type_ == 0:
            key_ = 'song'
        elif type_ == 8:
            key_ = 'album'
        elif type_ == 9:
            key_ = 'singer'
        else:
            raise QQIOError('invalid search type_:%d', type_)
        payload = {
            "search": {
                "method": "DoSearchForQQMusicDesktop",
                "module": "music.search.SearchCgiService",
                "param": {
                    # People said that the max num_per_page is 30.
                    "num_per_page": max(limit, 30),
                    "page_num": page,
                    "search_type": type_,
                    "query": keyword,
                }
            }
        }
        js = self.rpc(payload)
        result = js['search']['data']['body'][key_]['list']
        return result

    def search_playlists(self, query, limit=20, page=1):
        raise QQIOError('search api is not available')

    def song_detail(self, song_id):
        uin = self._uin
        song_id = int(song_id)
        # 往 payload 添加字段，有可能还可以获取相似歌曲、歌单等
        payload = {
            'comm': {
                'g_tk': 5381,
                'uin': uin,
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
        js = self.rpc(payload)
        data_song = js['detail']['data']['track_info']
        if data_song['id'] <= 0:
            return None
        return data_song

    def song_similar(self, song_id):
        payload = {
            "simsongs": {
                "module": "rcmusic.similarSongRadioServer",
                "method": "get_simsongs",
                "param": {
                    "songid": song_id,
                }
            }
        }
        js = self.rpc(payload)
        data_songs = js['simsongs']['data']['songInfoList']
        return data_songs

    def artist_detail(self, artist_mid):
        payload = {
            'req_0': {
                'module': 'music.musichallSinger.SingerInfoInter',
                'method': 'GetSingerDetail',
                'param': {
                    'singer_mids': [artist_mid],
                    'pic': 1,
                    'group_singer': 1,
                    'wiki_singer': 1,
                    'ex_singer': 1
                }},
            'comm': {
                'g_tk': self.get_token_from_cookies(),
                'uin': self._uin,
                'format': 'json',
            }
        }
        js = self.rpc(payload)
        data = js['req_0']['data']['singer_list'][0]
        data = {
            'singer_id': data['basic_info']['singer_id'],
            'singer_mid': data['basic_info']['singer_mid'],
            'singer_name': data['basic_info']['name'],
            'SingerDesc': data['ex_info']['desc'],
        }
        return data

    def artist_songs(self, artist_id, page=1, page_size=50):
        payload = {
            'req_0': {
                'module': 'music.musichallSong.SongListInter',
                'method': 'GetSingerSongList',
                'param': {
                    'singerid': artist_id,
                    'begin': (page - 1) * page_size,
                    'num': page_size,
                    # 有 newsong 字段时，服务端会返回含有 file 字段的字典
                    'newsong': 1
                }},
            'comm': {
                'g_tk': self.get_token_from_cookies(),
                'uin': self._uin,
                'format': 'json',
            }
        }
        js = self.rpc(payload)
        return js['req_0']['data']

    def artist_albums(self, artist_id, page=1, page_size=20):
        raise QQIOError('artist_albums api is not available')

    def album_detail(self, album_id):
        raise QQIOError('album_detail api is not available')

    def playlist_detail(self, pid, offset=0, limit=50):
        raise QQIOError('playlist_detail api is not available')

    def user_detail(self, uid):
        raise QQIOError('user_detail api is not available')

    def user_favorite_artists(self, uid, mid, page=1, page_size=30):
        # FIXME: page/page_size is just a guess
        payload = {
            'req_0': {
                'module': 'music.concern.RelationList',
                'method': 'GetFollowSingerList',
                'param': {
                    'From': page - 1,
                    'Size': page_size,
                    'HostUin': mid
                }},
            'comm': {
                'g_tk': self.get_token_from_cookies(),
                'uin': uid,
                'format': 'json',
            }
        }
        js = self.rpc(payload)
        return js['req_0']['data']['List']

    def user_favorite_albums(self, uid, start=0, end=100):
        raise QQIOError('user_detail api is not available')

    def user_favorite_playlists(self, uid, mid, start=0, end=100):
        raise QQIOError('api is not available')

    def get_recommend_songs_pid(self):
        data = {
            'req_0': {
                'module': 'recommend.RecommendFeedServer',
                'method': 'get_recommend_feed',
                'param': {
                    'direction': 0,
                    'page': 1,
                    'v_cache': [],
                    'v_uniq': [],
                    's_num': 0
                }
            },
        }
        js = self.rpc(data)
        disstid = js['req_0']['data']['v_shelf'][0]['v_niche'][0]['v_card'][1]['id']
        return disstid

    def recommend_playlists(self):
        data = {
            'recomPlaylist': {
                'module': "playlist.HotRecommendServer",
                'method': "get_hot_recommend",
                'param': {
                    'cmd': 2,
                    'async': 1
                }
            },
        }
        js = self.rpc(data)
        playlist = js['recomPlaylist']
        return playlist['data']['v_hot']

    def get_recommend_playlists_ids(self, index=0):
        data = {
            'req_0': {
                'module': 'recommend.RecommendFeedServer',
                'method': 'get_recommend_feed',
                'param': {
                    'direction': 0,
                    'page': 1,
                    'v_cache': [],
                    'v_uniq': [],
                    's_num': 0
                }
            },
        }
        js = self.rpc(data)
        ids = [card['id']
               for card in js['req_0']['data']['v_shelf'][index]['v_niche'][0]['v_card']]
        return ids

    def get_lyric_by_songmid(self, songmid):
        raise QQIOError('get_lyric_by_songmid is not available')

    def rpc(self, payload):
        if 'comm' not in payload:
            payload['comm'] = self.get_common_params()
        data_str = json.dumps(payload, ensure_ascii=False)
        params = {
            '_': int(round(time.time() * 1000)),
            'sign': _get_sign(data_str),
            'data': data_str,
        }
        url = 'https://u.y.qq.com/cgi-bin/musicu.fcg'
        resp = requests.get(url, params=params, headers=self._headers,
                            timeout=self._timeout)
        js = resp.json()
        CodeShouldBe0.check(js)
        return js

    def get_common_params(self):
        return {
            'loginUin': self._uin,
            'hostUin': 0,
            'g_tk': self.get_token_from_cookies(),
            'inCharset': 'utf8',
            'outCharset': 'utf-8',
            'notice': 0,
            'platform': 'yqq',
            'needNewCode': 0,
        }

    def get_mv(self, vid):
        payload = {
            'getMvUrl': {
                'module': "gosrf.Stream.MvUrlProxy",
                'method': "GetMvUrls",
                'param': {
                    "vids": [vid],
                    'request_typet': 10001
                }
            }
        }
        js = self.rpc(payload)
        return js['getMvUrl']['data'][vid]

    def get_radio_music(self):
        payload = {
            'songlist': {
                'module': "mb_track_radio_svr",
                'method': "get_radio_track",
                'param': {
                    'id': 99,
                    'firstplay': 1,
                    'num': 15
                },
            },
            'radiolist': {
                'module': "pf.radiosvr",
                'method': "GetRadiolist",
                'param': {
                    'ct': "24"
                },
            },
            'comm': {
                'ct': 24,
                'cv': 0
            },
        }
        js = self.rpc(payload)
        res_json = []
        for track in js['songlist']['data']['tracks']:
            track['songid'] = track.pop('id')
            track['songmid'] = track.pop('mid')
            track['songname'] = track.pop('name')
            res_json.append(track)
        return res_json

    def get_song_url(self, song_mid):
        uin = self._uin
        songvkey = str(random.random()).replace("0.", "")
        guid = self._guid
        # filename = f'C400{song_mid}.m4a'
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
                    "cid": 205361747,
                    "guid": guid,
                    "songmid": [song_mid],
                    # "filename": [filename],
                    "songtype": [1],
                    "uin": str(uin),  # NOTE: must be a string
                    # "loginflag": 1,
                    # "platform": "20"
                }
            },
            "comm": {
                "uin": uin,
                "format": "json",
                "ct": 24,
                "cv": 0
            }
        }
        data_str = json.dumps(data, ensure_ascii=False)
        params = {
            '-': 'getplaysongvkey' + str(songvkey),
            'g_tk': 5381,
            'loginUin': uin,
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
        # 如果是绿钻会员，这里带上 cookies，就能请求到收费歌曲的 url
        resp = requests.get(url, params=params,
                            headers=self._headers, cookies=self._cookies)
        js = resp.json()
        midurlinfo = js['req_0'].get('data', {}).get('midurlinfo')
        if midurlinfo:
            purl = midurlinfo[0]['purl']
            prefix = 'http://dl.stream.qqmusic.qq.com/'
            prefix = 'http://mobileoc.music.tc.qq.com/'

            # 经过个人(cosven)测试，无论是普通还是绿钻用户，下面几个都会失败
            quality_suffix = [
                # ('sq', 'M500', 'mp3'),
                # ('shq', 'F000', 'flac'),
                # ('hq', 'M800', 'mp3'),
                # ('shq', 'A000', 'ape'),
            ]
            C400_filename = midurlinfo[0]['filename']
            pure_filename = C400_filename[4:-3]

            req_data = js['req']['data']
            testfilewifi = req_data.get('testfilewifi', '')
            vkey = req_data['vkey']

            # 抓客户端的包，发现 guid/uin/vkey 三个参数配上对非常重要。
            # 尝试了客户端的 cookie 拷贝过来，还是请求不到无损音乐。
            if testfilewifi:
                params_str = testfilewifi.split('?')[1]
            else:
                params_str = f'vkey={vkey}&guid=MS&uin=0&fromtag=8'

            # 如果前两个音质都不行，我们认为后面的音乐也都不可以，
            # 目前通过这样简单的策略来节省请求次数
            max_try_count = 2
            failed_try_count = 0
            valid_urls = {}
            for quality, q, s in quality_suffix:
                if quality in valid_urls:
                    continue
                q_filename = q + pure_filename + s
                # 通过抓客户端接口可以发现，这个 uin 和用户 uin 不是一个东西
                # 这个 uin 似乎只有三位数
                url = f'{prefix}{q_filename}?{params_str}'
                print(url)
                _resp = requests.head(url, headers=self._headers, cookies=self._cookies)
                if _resp.status_code == 200:
                    valid_urls[quality] = url
                    logger.info(f'song:{song_mid} quality:{q} url is valid')
                    continue
                logger.info(f'song:{song_mid} quality:{q} url is invalid')
                failed_try_count += 1
                if failed_try_count >= max_try_count:
                    break
            # 尝试拿到网页版接口的 url
            if not valid_urls and purl:
                song_path = purl
                url = prefix + song_path
                valid_urls['lq'] = url
                logger.info(f'song:{song_mid} quality:web url is valid')
            return valid_urls
        return {}

    def get_song_url_v2(self, song_mid, media_id, quality):
        switcher = {
            'F000': 'flac',
            'A000': 'ape',
            'M800': 'mp3',
            'C600': 'm4a',
            'M500': 'mp3'
        }

        uin = self._uin
        guid = self._guid
        filename = '{}{}.{}'.format(quality, media_id, switcher.get(quality))
        data = {
            "req_0": {
                "module": "vkey.GetVkeyServer",
                "method": "CgiGetVkey",
                "param": {
                    "filename": [filename],
                    "guid": guid,
                    "songmid": [song_mid],
                    "songtype": [0],
                    "uin": str(uin),  # NOTE: must be a string
                    "loginflag": 1,
                    "platform": "20"
                }
            },
            "comm": {
                "uin": str(uin),
                "format": "json",
                "ct": 19,
                "cv": 0
            }
        }
        data_str = json.dumps(data, ensure_ascii=False)

        sign = _get_sign(data_str)
        params = {
            'sign': sign,
            'g_tk': 5381,
            'loginUin': '',
            'hostUin': 0,
            'format': 'json',
            'inCharset': 'utf8',
            'outCharset': 'utf-8¬ice=0',
            'platform': 'yqq.json',
            'needNewCode': 0,
            'data': data_str
        }
        url = 'https://u.y.qq.com/cgi-bin/musicu.fcg'
        # TODO: 似乎存在一种有效时间更长的cookies, https://github.com/PeterDing/chord
        resp = requests.get(url, params=params,
                            headers=self._headers, cookies=self._cookies)
        js = resp.json()
        midurlinfo = js['req_0'].get('data', {}).get('midurlinfo')
        if midurlinfo and midurlinfo[0]['purl']:
            return 'http://isure.stream.qqmusic.qq.com/{}'.format(midurlinfo[0]['purl'])
        return ''


api = API()
