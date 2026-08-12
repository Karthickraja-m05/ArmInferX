"""ArmServe CLI Package."""

from typing import Any

import click

# 1. Compatibility patch for Click 8.4+ and Typer 0.9 rich_utils:
# Fixes TypeError: Parameter.make_metavar() missing 1 required positional argument: 'ctx'
_orig_make_metavar = click.Parameter.make_metavar


def _compat_make_metavar(self: click.Parameter, ctx: click.Context | None = None) -> str:
    if ctx is not None:
        return _orig_make_metavar(self, ctx)
    try:
        current_ctx = click.get_current_context(silent=True)
        if current_ctx is not None:
            return _orig_make_metavar(self, current_ctx)
    except Exception:
        pass
    return self.metavar or (self.type.name.upper() if hasattr(self.type, "name") else "TEXT")


click.Parameter.make_metavar = _compat_make_metavar  # type: ignore[assignment]


# 2. Compatibility patch for Click 8.4+ option flag auto-detection:
# Fixes Click 8.4 treating short option aliases (-u, -k, -t, -c) as secondary boolean flags
_orig_option_init = click.Option.__init__


def _compat_option_init(
    self: click.Option, param_decls: list[str] | None = None, **attrs: Any
) -> None:
    if attrs.get("is_flag") is None and attrs.get("flag_value") is None:
        attrs["is_flag"] = False
    _orig_option_init(self, param_decls, **attrs)


click.Option.__init__ = _compat_option_init  # type: ignore[assignment]

__version__ = "0.1.0"
__all__ = ["__version__"]
