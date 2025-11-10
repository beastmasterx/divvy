"""
Internationalization (i18n) support for Divvy CLI.
Provides translation functions and language management.
"""

import gettext
import locale
import os
from pathlib import Path

# Get the directory where this module is located
_MODULE_DIR = Path(__file__).parent
# Locale directory is now in app/locale (one level up from core)
_LOCALE_DIR = _MODULE_DIR.parent / "locale"

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "en_US",
    "en_US": "en_US",
    "zh": "zh_CN",
    "zh_CN": "zh_CN",
    "zh_CN.UTF-8": "zh_CN",
}

# Default language
DEFAULT_LANGUAGE = "en_US"

# Global translation object
_translation = None


def get_language() -> str:
    """
    Determines the language to use.

    Priority:
    1. DIVVY_LANG environment variable
    2. LANG environment variable
    3. System locale
    4. Default (en_US)

    Returns:
        Language code (e.g., "en_US", "zh_CN")
    """
    # Check DIVVY_LANG first (application-specific)
    divvy_lang = os.getenv("DIVVY_LANG")
    if divvy_lang:
        normalized = SUPPORTED_LANGUAGES.get(divvy_lang)
        if normalized:
            return normalized

    # Check LANG environment variable
    lang_env = os.getenv("LANG", "")
    if lang_env:
        # Extract language code (e.g., "zh_CN.UTF-8" -> "zh_CN")
        lang_base = lang_env.split(".")[0]
        normalized = SUPPORTED_LANGUAGES.get(lang_base)
        if normalized:
            return normalized

    # Try system locale
    try:
        system_locale, _ = locale.getlocale()
        if system_locale:
            lang_base = system_locale.split(".")[0] if "." in system_locale else system_locale
            normalized = SUPPORTED_LANGUAGES.get(lang_base)
            if normalized:
                return normalized
    except (AttributeError, ValueError):
        pass

    return DEFAULT_LANGUAGE


def set_language(lang: str | None = None) -> str:
    """
    Sets the language for translations.

    Args:
        lang: Language code (e.g., "en_US", "zh_CN", "zh", "en").
              If None, auto-detects from environment.

    Returns:
        The language code that was set
    """
    global _translation

    if lang:
        normalized = SUPPORTED_LANGUAGES.get(lang)
        if not normalized:
            normalized = DEFAULT_LANGUAGE
    else:
        normalized = get_language()

    # Set up gettext
    try:
        _translation = gettext.translation(
            "divvy",
            localedir=str(_LOCALE_DIR),
            languages=[normalized],
            fallback=True,
        )
    except FileNotFoundError:
        # If translation files don't exist, use fallback (English)
        _translation = gettext.NullTranslations()

    return normalized


def _(message: str) -> str:
    """
    Translate a message.

    Args:
        message: The message to translate

    Returns:
        Translated message
    """
    if _translation is None:
        set_language()

    return _translation.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """
    Translate a message with pluralization.

    Args:
        singular: Singular form
        plural: Plural form
        n: Number to determine singular/plural

    Returns:
        Translated message with correct plural form
    """
    if _translation is None:
        set_language()

    return _translation.ngettext(singular, plural, n)


# Initialize translation on import
set_language()


def _get_category_translations() -> dict[str, str]:
    """Get category translations dictionary (called after language is set)."""
    return {
        "Utilities (Water & Electricity & Gas)": _("Utilities (Water & Electricity & Gas)"),
        "Groceries": _("Groceries"),
        "Daily Necessities": _("Daily Necessities"),
        "Rent": _("Rent"),
        "Other": _("Other"),
    }


def translate_category(category_name: str) -> str:
    """
    Translates a category name.

    Args:
        category_name: The category name from database

    Returns:
        Translated category name
    """
    translations = _get_category_translations()
    return translations.get(category_name, category_name)


def translate_transaction_type(transaction_type: str) -> str:
    """
    Translates a transaction type.

    Args:
        transaction_type: Transaction type ('expense', 'deposit', or special case)

    Returns:
        Translated transaction type
    """
    type_map = {
        "expense": _("Expense"),
        "deposit": _("Deposit"),
        "refund": _("Refund"),
    }
    return type_map.get(transaction_type.lower(), transaction_type.title())
