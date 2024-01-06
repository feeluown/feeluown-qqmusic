import logging

from .provider import provider

__alias__ = 'QQ 音乐'
__feeluown_version__ = '1.1.0'
__version__ = '0.3a0'
__desc__ = 'QQ 音乐'

logger = logging.getLogger(__name__)


def enable(app):
    app.library.register(provider)
    if app.mode & app.GuiMode:
        from .provider_ui import ProviderUI

        provider_ui = ProviderUI(app)
        app.pvd_ui_mgr.register(provider_ui)


def disable(app):
    app.library.deregister(provider)
    if app.mode & app.GuiMode:
        app.providers.remove(provider.identifier)
