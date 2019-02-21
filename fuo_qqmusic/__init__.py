# -*- coding: utf-8 -*-

import logging

from feeluown.app import App

from .provider import provider

__alias__ = 'QQ 音乐'
__feeluown_version__ = '1.1.0'
__version__ = '0.1a0'
__desc__ = 'QQ 音乐'

logger = logging.getLogger(__name__)


def enable(app):
    app.library.register(provider)
    if app.mode & App.GuiMode:
        pm = app.pvd_uimgr.create_item(
            name=provider.identifier,
            text='QQ 音乐',
            symbol='♫ ',
            desc='点击登录 QQ 音乐（未实现，欢迎 PR）',
        )
        app.pvd_uimgr.add_item(pm)


def disable(app):
    app.library.deregister(provider)
    if app.mode & App.GuiMode:
        app.providers.remove(provider.identifier)
