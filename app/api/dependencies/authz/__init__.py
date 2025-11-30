"""
Authorization (authz) Package 🛡️

This package contains all policy enforcement dependencies, determining
'What the authenticated user is allowed to do.'

Policies are grouped by type (RBAC, ABAC) and raise a 403 Forbidden error on failure.
All policies depend on providers from the 'authn' package.

---
VERB CONVENTION: Authorization Verbs (All use Singular Verb form)

1.  requires_*: Enforces static **RBAC (Role-Based Access Control)** requirements
    (e.g., role, minimum permission). Focuses on **necessity**.
2.  verifies_*: Enforces high-stakes **ABAC (Attribute-Based Access Control)** checks, identity proofs, or ownership. Focuses on **rigorous proof**.
3.  checks_*: Enforces simple **contextual or environmental constraints** (e.g.,
    time of day, status flags). Focuses on **simple conditions**.

---
IMPORTANT: Exclusion of 'validate_'
The verb 'validate_' is **reserved exclusively** for dependencies concerning
**Data Integrity and Schema** (format/type checking). It is NOT used for
Authorization, as Authorization failures result in a **403 Forbidden** error,
while Data Integrity failures result in a **422 Unprocessable Entity** error.

"""

from .rbac import requires_group_role, requires_group_role_for_period, requires_system_role

__all__ = [
    "requires_group_role",
    "requires_group_role_for_period",
    "requires_system_role",
]
