"""
CLI package for Divvy application.
Re-exports main functions from cli.main for convenience.
Uses lazy imports to avoid RuntimeWarning when running via 'python -m cli.main'.
"""


def __getattr__(name):
    """Lazy import to avoid RuntimeWarning when running as module."""
    if name in ("main", "show_menu", "select_from_list", "select_payer", "select_period"):
        # Use importlib to import the module directly, avoiding circular import
        import importlib
        # Import cli.main module (this will work even if it's already in sys.modules)
        main_module = importlib.import_module("cli.main")
        # Get the attribute and cache it
        attr = getattr(main_module, name)
        globals()[name] = attr
        return attr
    
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "main",
    "show_menu",
    "select_from_list",
    "select_payer",
    "select_period",
]
