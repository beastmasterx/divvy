"""
Registry for identity provider implementations.
"""

from .base import IdentityProvider


class IdentityProviderRegistry:
    """Registry for identity provider implementations."""

    _providers: dict[str, IdentityProvider] = {}

    @classmethod
    def register(cls, provider: IdentityProvider) -> None:
        """Register a provider instance.

        Args:
            provider: Provider instance to register
        """
        cls._providers[provider.name] = provider

    @classmethod
    def get_provider(cls, name: str) -> IdentityProvider:
        """Get provider by name.

        Args:
            name: Provider name (e.g., 'microsoft', 'google')

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is not registered
        """
        if name not in cls._providers:
            raise ValueError(f"Unknown identity provider: {name}")
        return cls._providers[name]

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a provider is registered.

        Args:
            name: Provider name

        Returns:
            True if provider is registered, False otherwise
        """
        return name in cls._providers

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a provider by name.

        Args:
            name: Provider name to unregister

        Note:
            This method is primarily useful for testing. In production,
            providers are typically registered once and remain registered.
        """
        cls._providers.pop(name, None)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers.

        Note:
            This method is primarily useful for testing. In production,
            this should not be called as it will remove all registered providers.
        """
        cls._providers.clear()


# Auto-register providers on module import
# from .microsoft import MicrosoftProvider
# _microsoft_provider = MicrosoftProvider()
# IdentityProviderRegistry.register(_microsoft_provider)
#
# from .google import GoogleProvider
# _google_provider = GoogleProvider()
# IdentityProviderRegistry.register(_google_provider)
