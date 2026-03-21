from pathlib import Path
from fluent.runtime import FluentLocalization, FluentResourceLoader
from feeluown.i18n import _DEFAULT_LOCALE

_DIR = Path(__file__).parent
_l10n = None

def t(msg_id: str, **kwargs) -> str:
    global _l10n
    if _l10n is None:
        loader = FluentResourceLoader(roots=[str(_DIR / "{locale}")])
        _l10n = FluentLocalization(
            locales=[_DEFAULT_LOCALE, "zh-CN", "en-US", "ja-JP"],
            resource_ids=["provider.ftl"],
            resource_loader=loader,
        )
    return _l10n.format_value(msg_id, kwargs)
