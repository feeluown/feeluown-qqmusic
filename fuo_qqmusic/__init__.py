import logging
from pathlib import Path

from feeluown.i18n import register_plugin_i18n

from .provider import provider
from .consts import domain

__alias__ = 'QQ 音乐'
__feeluown_version__ = '1.1.0'
__version__ = '0.3a0'
__desc__ = 'QQ 音乐'

logger = logging.getLogger(__name__)


def enable(app):
    locales_dir = Path(__file__).parent / "locales"
    resource_ids = ["main.ftl"]
    register_plugin_i18n(domain=domain, locales_dir=locales_dir,
                         resource_ids=resource_ids)
    app.library.register(provider)
    if app.mode & app.GuiMode:
        from .provider_ui import ProviderUI

        provider_ui = ProviderUI(app)
        app.pvd_ui_mgr.register(provider_ui)


def disable(app):
    app.library.deregister(provider)
    if app.mode & app.GuiMode:
        app.providers.remove(provider.identifier)
