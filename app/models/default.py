"""
Default data for seeding the database.
"""

# Default categories for transactions
categories = [
    "Utilities (Water & Electricity & Gas)",
    "Groceries",
    "Daily Necessities",
    "Rent",
    "Settlement",
    "Other",
]

# Default role-permission mappings
# Format: (role, permission)
# Note: 'system:admin' and 'group:owner' are not included as they bypass permission checks
role_permissions = [
    # System Role: system:user
    ("system:user", "groups:read"),
    # Group Role: group:admin
    ("group:admin", "groups:read"),
    ("group:admin", "groups:write"),
    ("group:admin", "transactions:read"),
    ("group:admin", "transactions:write"),
    ("group:admin", "transactions:delete"),
    ("group:admin", "periods:read"),
    ("group:admin", "periods:write"),
    ("group:admin", "periods:delete"),
    # Group Role: group:member
    ("group:member", "transactions:read"),
    ("group:member", "transactions:write"),
    ("group:member", "periods:read"),
]
