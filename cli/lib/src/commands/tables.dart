// Table formatting utilities for displaying data.

import '../utils/formatting.dart';
import '../utils/i18n.dart';

/// Display a simple table with headers and rows in TSV format (kubectl style).
void displayTable({required List<String> headers, required List<List<String>> rows}) {
  if (rows.isEmpty) {
    print(translate('No data available.'));
    return;
  }

  // Print header (tab-separated)
  print(headers.join('\t'));

  // Print rows (tab-separated)
  for (final row in rows) {
    // Ensure row has same number of columns as headers (pad with empty strings if needed)
    final paddedRow = List<String>.from(row);
    while (paddedRow.length < headers.length) {
      paddedRow.add('');
    }
    // Truncate if row has more columns than headers
    if (paddedRow.length > headers.length) {
      paddedRow.removeRange(headers.length, paddedRow.length);
    }
    print(paddedRow.join('\t'));
  }
}

/// Display a list of items with numbers for selection.
void displayList<T>({required List<T> items, required String Function(T) itemToString, String? header}) {
  if (items.isEmpty) {
    print(translate('No items available.'));
    return;
  }

  if (header != null) {
    print(header);
    print('-' * getDisplayWidth(header));
  }

  for (int i = 0; i < items.length; i++) {
    print('${i + 1}. ${itemToString(items[i])}');
  }
}

/// Format amount in cents to dollars with sign.
String formatAmount(int cents) {
  return formatAmountWithSign(cents);
}

/// Format date/time.
String formatDateTime(DateTime dateTime) {
  return '${dateTime.year}-${dateTime.month.toString().padLeft(2, '0')}-${dateTime.day.toString().padLeft(2, '0')} '
      '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
}
