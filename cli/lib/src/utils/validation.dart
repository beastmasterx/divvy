// Utility functions for input validation.

/// Validate and parse a dollar amount string.
///
/// Accepts formats like: "123.45", "123", "$123.45", "123.456" (rounds to 2 decimals)
///
/// Parameters:
/// - [amountStr]: The amount string to validate
///
/// Returns:
/// A tuple of (isValid, amountInCents, errorMessage)
/// - isValid: true if the amount is valid
/// - amountInCents: The amount in cents (0 if invalid)
/// - errorMessage: Error message if invalid, empty string if valid
({bool isValid, int amountInCents, String errorMessage}) validateAmount(
  String amountStr,
) {
  if (amountStr.trim().isEmpty) {
    return (
      isValid: false,
      amountInCents: 0,
      errorMessage: 'Amount cannot be empty.',
    );
  }

  // Remove dollar sign and whitespace
  final cleaned = amountStr.replaceAll('\$', '').trim();

  // Try to parse as double
  final amount = double.tryParse(cleaned);
  if (amount == null) {
    return (
      isValid: false,
      amountInCents: 0,
      errorMessage:
          'Invalid amount format. Please enter a number (e.g., "123.45").',
    );
  }

  if (amount <= 0) {
    return (
      isValid: false,
      amountInCents: 0,
      errorMessage: 'Amount must be greater than zero.',
    );
  }

  // Convert to cents (round to nearest cent)
  final cents = (amount * 100).round();

  return (isValid: true, amountInCents: cents, errorMessage: '');
}

/// Validate an email address.
///
/// Parameters:
/// - [email]: The email to validate
///
/// Returns:
/// true if the email is valid, false otherwise
bool validateEmail(String email) {
  if (email.trim().isEmpty) {
    return false;
  }

  // Basic email validation regex
  final emailRegex = RegExp(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
  );

  return emailRegex.hasMatch(email.trim());
}

/// Validate a member name.
///
/// Parameters:
/// - [name]: The name to validate
///
/// Returns:
/// A tuple of (isValid, errorMessage)
({bool isValid, String errorMessage}) validateName(String name) {
  if (name.trim().isEmpty) {
    return (isValid: false, errorMessage: 'Name cannot be empty.');
  }

  return (isValid: true, errorMessage: '');
}

/// Validate a period name (optional, can be empty for auto-generation).
///
/// Parameters:
/// - [periodName]: The period name to validate
///
/// Returns:
/// true if valid (empty is valid), false otherwise
bool validatePeriodName(String periodName) {
  // Period name is optional, empty string is valid (will auto-generate)
  return true;
}
