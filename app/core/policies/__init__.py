"""
ABAC (Attribute-Based Access Control) policy infrastructure.

This module provides the core infrastructure for declarative policy enforcement.
Policies are registered when their modules are imported at application startup.

Key components:
- PolicyRegistry: Central registry for policy functions
- get_policy_registry: Access to the global policy registry instance

Example:
    # In app/api/dependencies/policies/financial_reports.py
    from app.core.policies import register
    from app.exceptions import ForbiddenError

    @register("managers_can_delete_financial_reports")
    async def policy_managers_can_delete_financial_reports(
        service,
        report_id: int,
        current_user_id: int,
        current_time: str,
        network: str,
    ):
        # Subject attributes
        user = await service.get_user(current_user_id)
        if user.role != 'manager':
            raise ForbiddenError("Only managers can delete financial reports")

        # Resource attributes
        report = await service.get_report(report_id)
        if report.type != 'financial':
            raise ForbiddenError("Only financial reports can be deleted")

        # Subject and Resource matching
        if user.department != report.department:
            raise ForbiddenError("Managers can only delete reports from their own department")

        # Environment attributes
        hour = int(current_time.split(':')[0])
        if hour < 9 or hour >= 17:
            raise ForbiddenError("Financial reports can only be deleted during business hours")

        if network != 'corporate':
            raise ForbiddenError("Financial reports can only be deleted from corporate network")

    # Policies are automatically registered when the module is imported.
    # Ensure policy modules are imported at application startup (e.g., in main.py):
    # import app.api.dependencies.policies.financial_reports  # This triggers registration
"""

from app.core.policies.registry import (
    PolicyRegistry,
    get_policy_registry,
)


# Convenience function for registering policies
def register(policy_name: str):
    """Convenience function to register a policy.

    This is a shortcut for get_policy_registry().register(policy_name).

    Args:
        policy_name: Unique name for the policy

    Returns:
        Decorator function that registers the policy when applied to a function

    Example:
        from app.core.policies import register

        @register("managers_can_delete_financial_reports")
        async def policy_managers_can_delete_financial_reports(...):
            ...
    """
    return get_policy_registry().register(policy_name)


__all__ = [
    "PolicyRegistry",
    "register",
]
