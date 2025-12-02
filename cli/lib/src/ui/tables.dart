// Table formatting utilities for displaying data.

import '../utils/formatting.dart';
import '../utils/i18n.dart';

/// Display a simple table with headers and rows.
void displayTable({
  required List<String> headers,
  required List<List<String>> rows,
}) {
  if (rows.isEmpty) {
    print(translate('No data available.'));
    return;
  }

  // Calculate column widths
  final widths = List<int>.filled(headers.length, 0);
  for (int i = 0; i < headers.length; i++) {
    widths[i] = getDisplayWidth(headers[i]);
  }
  for (final row in rows) {
    for (int i = 0; i < row.length && i < widths.length; i++) {
      final width = getDisplayWidth(row[i]);
      if (width > widths[i]) {
        widths[i] = width;
      }
    }
  }

  // Print header
  final headerRow = headers.asMap().entries.map((e) {
    return padToDisplayWidth(e.value, widths[e.key], '<');
  }).join(' | ');
  print(headerRow);
  print('-' * getDisplayWidth(headerRow));

  // Print rows
  for (final row in rows) {
    final rowStr = row.asMap().entries.map((e) {
      if (e.key < widths.length) {
        return padToDisplayWidth(e.value, widths[e.key], '<');
      }
      return e.value;
    }).join(' | ');
    print(rowStr);
  }
}

/// Display a list of items with numbers for selection.
void displayList<T>({
  required List<T> items,
  required String Function(T) itemToString,
  String? header,
}) {
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

