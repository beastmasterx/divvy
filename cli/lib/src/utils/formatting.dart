// Utility functions for text formatting and display width calculation.
//
// Supports wide characters (CJK, emoji, etc.) where each wide character
// counts as 2 display units instead of 1.

/// Calculate display width of text for table alignment.
///
/// Chinese/wide characters count as 2, ASCII as 1.
///
/// Parameters:
/// - [text]: The text to measure
///
/// Returns:
/// The display width of the text
int getDisplayWidth(String text) {
  int width = 0;
  for (final char in text.runes) {
    // Check if character is wide (Chinese, Japanese, Korean, etc.)
    // Unicode ranges for wide characters
    if (char > 0x1100) {
      // Wide characters (CJK, emoji, etc.) - approximate check
      if ((char >= 0x2E80 && char <= 0x9FFF) || // CJK Unified Ideographs
          (char >= 0xAC00 && char <= 0xD7AF) || // Hangul
          (char >= 0x3040 && char <= 0x309F) || // Hiragana
          (char >= 0x30A0 && char <= 0x30FF) || // Katakana
          (char >= 0xFF00 && char <= 0xFFEF)) {
        // Fullwidth chars
        width += 2;
      } else {
        width += 1;
      }
    } else {
      width += 1;
    }
  }
  return width;
}

/// Pad text to target display width, accounting for wide characters.
///
/// Parameters:
/// - [text]: The text to pad
/// - [targetWidth]: The target display width
/// - [align]: Alignment: '<' for left, '>' for right, '^' for center (default: '<')
///
/// Returns:
/// The padded text
String padToDisplayWidth(String text, int targetWidth, [String align = '<']) {
  final currentWidth = getDisplayWidth(text);
  if (currentWidth >= targetWidth) {
    return text;
  }

  final paddingNeeded = targetWidth - currentWidth;

  switch (align) {
    case '<':
      return text + (' ' * paddingNeeded);
    case '>':
      return (' ' * paddingNeeded) + text;
    case '^':
      final leftPad = paddingNeeded ~/ 2;
      final rightPad = paddingNeeded - leftPad;
      return (' ' * leftPad) + text + (' ' * rightPad);
    default:
      return text + (' ' * paddingNeeded);
  }
}

/// Format a dollar amount from cents to dollars string.
///
/// Parameters:
/// - [cents]: Amount in cents
///
/// Returns:
/// Formatted dollar string (e.g., "123.45")
String centsToDollars(int cents) {
  final dollars = cents.abs() / 100.0;
  return dollars.toStringAsFixed(2);
}

/// Format a dollar amount with sign.
///
/// Parameters:
/// - [cents]: Amount in cents
///
/// Returns:
/// Formatted string with sign (e.g., "+$123.45" or "-$67.89")
String formatAmountWithSign(int cents) {
  final sign = cents >= 0 ? '+' : '-';
  final amount = centsToDollars(cents.abs());
  return '$sign\$$amount';
}

/// Get the string name from an EnumClass instance.
///
/// This extracts the enum value name (e.g., "open", "draft") from an EnumClass.
/// EnumClass stores the name internally, and this helper provides a clean way to access it.
///
/// Parameters:
/// - [enumValue]: The EnumClass instance
///
/// Returns:
/// The string name of the enum value
String getEnumName(dynamic enumValue) {
  // EnumClass stores the name, accessible via toString().split('.').last
  // This is cleaner than repeating the pattern everywhere
  return enumValue.toString().split('.').last;
}
