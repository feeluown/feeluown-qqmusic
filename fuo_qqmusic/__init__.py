import logging

from feeluown.app import App

from .provider import provider
from .ui import UiManager

__alias__ = 'QQ 音乐'
__feeluown_version__ = '1.1.0'
__version__ = '0.3a0'
__desc__ = 'QQ 音乐'

logger = logging.getLogger(__name__)
ui_mgr = None


def enable(app):
    global ui_mgr
    app.library.register(provider)
    if app.mode & App.GuiMode:
        ui_mgr = ui_mgr or UiManager(app)


def disable(app):
    app.library.deregister(provider)
    if app.mode & App.GuiMode:
        app.providers.remove(provider.identifier)
