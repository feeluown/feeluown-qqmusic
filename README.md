# feeluown QQ 音乐插件

[![Build Status](https://travis-ci.com/feeluown/feeluown-qqmusic.svg?branch=master)](https://travis-ci.com/feeluown/feeluown-qqmusic)
[![PyPI](https://img.shields.io/pypi/v/fuo_qqmusic.svg)](https://pypi.python.org/pypi/fuo-qqmusic)
[![Coverage Status](https://coveralls.io/repos/github/feeluown/feeluown-qqmusic/badge.svg?branch=master)](https://coveralls.io/github/feeluown/feeluown-qqmusic?branch=master)


2023-06-08：该插件可以和老版本 FeelUOwn(\<v3.9) 一起使用。

## 安装

```sh
pip3 install fuo-qqmusic
```

## 使用说明

### 登录
在网页登录微信/QQ后（在任意网站），复制请求中的 cookies 至程序登录框，
[操作示例](https://github.com/feeluown/feeluown-qqmusic/issues/6)。

## changelog

### 0.5.0 (2023-07-14)

- 修复搜索接口
- 让部分不可用接口直接报错

### 0.4.1 (2022-03-21)

- 修复加载歌单时，应用可能会 crash 的问题

### 0.4.0 (???)

- 修复若干问题

### 0.3.4 (2022-01-31)

感谢 [@cyliuu](https://github.com/cyliuu)

- 修复若干问题

### 0.3.3 (2021-06-10)

感谢 [@cyliuu](https://github.com/cyliuu)

- 支持展示收藏的歌曲、专辑和歌手
- 支持获取相似歌曲

### 0.3.2 (2021-04-23)

感谢 [@cyliuu](https://github.com/cyliuu)

- 提供更准确的音乐的比特率
- 绿钻用户使用合适的 cookie 可以获取到高品质音乐

### 0.3 (2020-08-10)

感谢 [@csy19960309](https://github.com/csy19960309)

- 支持登陆功能，加载用户歌单
- 支持歌词和 mv
- 绿钻用户可以播放任意歌曲，但不能选音质

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
