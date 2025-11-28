"""
ABAC (Attribute-Based Access Control) policy infrastructure.

ABAC evaluates access control decisions based on four attribute categories:

- Subject: Attributes of the entity requesting access (user_id, role, department, clearance_level)
- Resource: Attributes of the object being accessed (resource_id, type, owner, sensitivity_level)
- Action: The operation being performed (read, write, delete, execute)
- Environment: Contextual factors at the time of access (time, location, IP_address, device_type)

A policy is a function that evaluates these attributes and determines whether an access
request should be allowed or denied. Unlike role-based access control (RBAC), ABAC
enables fine-grained, context-aware authorization decisions that can implement complex
business rules and dynamic access control.

Example:
    Policy: "Managers can delete financial reports from their own department
    during business hours when accessing from corporate network."

    Evaluation:
    - Subject: user.role='manager', user.department='sales'
    - Resource: report.type='financial', report.department='sales', report.owner_id=123
    - Action: 'delete'
    - Environment: current_time='14:30', day='weekday', network='corporate'

    Decision: Allow - all conditions met (matching department, business hours, corporate network)

    If environment was network='public' or time='22:00', the policy would deny access
    even though the user has manager role and owns the resource.
"""

from collections.abc import Awaitable, Callable


class PolicyRegistry:
    """Registry for ABAC policy functions.

    The registry maintains a collection of registered policy functions that evaluate
    access control decisions based on subject, resource, action, and environment attributes.
    Policies are async functions that receive context (service instances, parameters,
    request context) and determine whether access should be granted or denied.

    Policies should raise ForbiddenError or BusinessRuleError if access should be denied.
    If a policy completes without raising an exception, access is granted.
    """

    def __init__(self) -> None:
        """Initialize an empty policy registry."""
        self._policies: dict[str, Callable[..., Awaitable[None]]] = {}

    def register(self, policy_name: str) -> Callable[[Callable[..., Awaitable[None]]], Callable[..., Awaitable[None]]]:
        """Register a policy function with the registry.

        Args:
            policy_name: Unique name for the policy (e.g., "only_owner_can_delete")

        Returns:
            Decorator function that registers the policy when applied to a function

        Raises:
            ValueError: If a policy with the same name is already registered

        Example:
            @registry.register("managers_can_delete_financial_reports")
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
        """

        def decorator(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
            if policy_name in self._policies:
                raise ValueError(f"Policy '{policy_name}' is already registered")
            self._policies[policy_name] = func
            return func

        return decorator

    def get_policy(self, policy_name: str) -> Callable[..., Awaitable[None]]:
        """Retrieve a registered policy function by name.

        Args:
            policy_name: Name of the policy to retrieve

        Returns:
            The registered policy function (async callable)

        Raises:
            ValueError: If policy is not registered. The error message includes
                       a list of available policy names for debugging.
        """
        if policy_name not in self._policies:
            raise ValueError(f"Unknown ABAC policy: {policy_name}. Available policies: {list(self._policies.keys())}")
        return self._policies[policy_name]

    def list_policies(self) -> list[str]:
        """List all registered policy names.

        Returns:
            List of all registered policy names, useful for debugging and introspection
        """
        return list(self._policies.keys())


# Global policy registry instance
_policy_registry = PolicyRegistry()


def get_policy_registry() -> PolicyRegistry:
    """Get the global policy registry instance.

    Returns:
        The singleton PolicyRegistry instance used throughout the application
    """
    return _policy_registry
