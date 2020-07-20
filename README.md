# feeluown QQ 音乐插件

[![Build Status](https://travis-ci.com/feeluown/feeluown-qqmusic.svg?branch=master)](https://travis-ci.com/feeluown/feeluown-qqmusic)
[![PyPI](https://img.shields.io/pypi/v/fuo_qqmusic.svg)](https://pypi.python.org/pypi/fuo-qqmusic)
[![Coverage Status](https://coveralls.io/repos/github/feeluown/feeluown-qqmusic/badge.svg?branch=master)](https://coveralls.io/github/feeluown/feeluown-qqmusic?branch=master)

## 安装

```sh
pip3 install fuo-qqmusic
```

## 登陆

在网页登录微信/QQ后（在任意网站），复制请求中的cookie至程序登录框

## 此版本的问题
- 播放列表初始化时有强烈卡顿 
- 请求失败会导致程序闪退
- 其他未知bug

## changelog

### 0.3 (2020-07-16)
- 支持登陆功能，登录后可播放付费音乐（如果账号有权限），可读取日推、播放列表、已收藏专辑和私人FM. 此外所有音乐新增歌词和MV功能。

### 0.2 (2019-11-27)
- 使用 marshmallow>=3.0 

### 0.1.5 (2019-10-28)
- 支持获取歌手的所有歌曲与专辑

### 0.1.4 (2019-08-20)
- 修复获取部分歌曲链接失败

### 0.1.3 (2019-05-25)
- 给歌曲链接添加过期时间

### 0.1.2 (2019-03-27)
- 获取音乐链接时，先尝试 M500 品质的，再尝试使用网页版接口返回的
  (测试发现：部分歌曲网页版接口拿不到链接，所以修改策略)

### 0.1.1 (2019-03-19)
- 获取音乐链接时，使用和网页一样的接口

### 0.1 (2019-03-18)
- 简单的搜索功能，歌曲、歌手、专辑详情查看

