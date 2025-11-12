// Internationalization utilities for translations.
//
// Uses a simple translation map approach. Can be extended to use
// the `intl` package later if needed.

/// Current language (default: 'en')
String _currentLanguage = 'en';

/// Translation map for English
final Map<String, String> _translationsEn = {
  // Menu
  'Divvy Expense Splitter': 'Divvy Expense Splitter',
  'Current Period: {}': 'Current Period: {}',
  '1. Add Expense': '1. Add Expense',
  '2. Add Deposit': '2. Add Deposit',
  '3. Add Refund': '3. Add Refund',
  '4. View Period': '4. View Period',
  '5. Close period': '5. Close period',
  '6. Add member': '6. Add member',
  '7. Remove Member': '7. Remove Member',
  '8. Exit': '8. Exit',
  'Enter your choice: ': 'Enter your choice: ',
  'Enter your choice (1-{}): ': 'Enter your choice (1-{}): ',
  'Enter your choice (1-{}, or Enter for default): ':
      'Enter your choice (1-{}, or Enter for default): ',
  'Invalid choice. Please enter a number between 1 and {}.':
      'Invalid choice. Please enter a number between 1 and {}.',
  'Invalid input. Please enter a number.':
      'Invalid input. Please enter a number.',
  'Input cannot be empty. Please enter a number.':
      'Input cannot be empty. Please enter a number.',
  'No {} available.': 'No {} available.',
  '\n--- Select {} ---': '\n--- Select {} ---',
  '------------------------': '------------------------',

  // Periods
  'No active period found.': 'No active period found.',
  'Period not found.': 'Period not found.',
  'No periods available.': 'No periods available.',
  'Period': 'Period',
  ' [Current]': ' [Current]',
  'Period selection cancelled.': 'Period selection cancelled.',
  'Active': 'Active',
  'Settled': 'Settled',
  'Started: {} | Active': 'Started: {} | Active',
  'Started: {} | Settled: {}': 'Started: {} | Settled: {}',
  'Deposits: {} | Expenses: {} | Fund: {}{}':
      'Deposits: {} | Expenses: {} | Fund: {}{}',

  // Transactions
  '\n--- Transactions ({}) ---': '\n--- Transactions ({}) ---',
  '\n--- Transactions (0) ---': '\n--- Transactions (0) ---',
  '  No transactions in this period.': '  No transactions in this period.',
  'Date': 'Date',
  'Category': 'Category',
  'Type': 'Type',
  'Split': 'Split',
  'Amount': 'Amount',
  'Description': 'Description',
  'From/To': 'From/To',
  'Payer: {}': 'Payer: {}',
  'From: {}': 'From: {}',
  'To: {}': 'To: {}',

  // Transaction types
  'Expense': 'Expense',
  'Deposit': 'Deposit',
  'Refund': 'Refund',

  // Split types
  'Shared': 'Shared',
  'Personal': 'Personal',
  'Individual': 'Individual',

  // Balances
  '\n--- Balances ({} active) ---': '\n--- Balances ({} active) ---',
  '\n--- Balances (0 active) ---': '\n--- Balances (0 active) ---',
  '  No active members.': '  No active members.',

  // Settlement
  '\n--- Settlement Plan ---': '\n--- Settlement Plan ---',
  'No settlement transactions needed (all balances already zero).':
      'No settlement transactions needed (all balances already zero).',
  '----------------------\n': '----------------------\n',

  // Members
  'No active members available.': 'No active members available.',
  'Payer': 'Payer',
  'Member to refund': 'Member to refund',
  'Member to remove': 'Member to remove',

  // Messages
  'Exiting Divvy. Goodbye!': 'Exiting Divvy. Goodbye!',
  'Invalid choice, please try again.': 'Invalid choice, please try again.',
  'Expense recording cancelled.': 'Expense recording cancelled.',
  'Deposit recording cancelled.': 'Deposit recording cancelled.',
  'Refund cancelled.': 'Refund cancelled.',
  'Member removal cancelled.': 'Member removal cancelled.',
  'Rejoin cancelled.': 'Rejoin cancelled.',

  // Errors
  'Error: Amount cannot be empty.': 'Error: Amount cannot be empty.',
  'Member email cannot be empty.': 'Member email cannot be empty.',
  'Member name cannot be empty.': 'Member name cannot be empty.',
  'Unknown': 'Unknown',

  // Category translations
  'Utilities (Water & Electricity & Gas)':
      'Utilities (Water & Electricity & Gas)',
  'Groceries': 'Groceries',
  'Daily Necessities': 'Daily Necessities',
  'Rent': 'Rent',
  'Other': 'Other',
};

/// Get translation for a key, with optional format arguments.
///
/// Parameters:
/// - [key]: The translation key
/// - [args]: Optional arguments for string formatting (using {})
///
/// Returns:
/// The translated string with arguments substituted
String translate(String key, [List<Object>? args]) {
  final translation = _translationsEn[key] ?? key;

  if (args == null || args.isEmpty) {
    return translation;
  }

  // Simple {} replacement
  String result = translation;
  for (final arg in args) {
    result = result.replaceFirst('{}', arg.toString());
  }
  return result;
}

/// Alias for translate() - matches Python's _() function.
// ignore: unused_element
String _(String key, [List<Object>? args]) => translate(key, args);

/// Translate a category name.
///
/// Parameters:
/// - [categoryName]: The category name from database
///
/// Returns:
/// Translated category name
String translateCategory(String categoryName) {
  return translate(categoryName);
}

/// Translate a transaction type.
///
/// Parameters:
/// - [transactionType]: Transaction type ('expense', 'deposit', 'refund')
///
/// Returns:
/// Translated transaction type
String translateTransactionType(String transactionType) {
  final lowerType = transactionType.toLowerCase();
  switch (lowerType) {
    case 'expense':
      return translate('Expense');
    case 'deposit':
      return translate('Deposit');
    case 'refund':
      return translate('Refund');
    default:
      return transactionType;
  }
}

/// Set the current language (for future i18n support).
///
/// Parameters:
/// - [lang]: Language code (e.g., 'en', 'zh_CN')
void setLanguage([String lang = 'en']) {
  _currentLanguage = lang;
  // Future: Load translations for the specified language
}

/// Get the current language.
String getCurrentLanguage() => _currentLanguage;
