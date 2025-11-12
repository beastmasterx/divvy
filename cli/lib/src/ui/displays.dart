// Display functions for showing period views, transactions, and balances.
//
// Provides formatted table displays with wide character support.

import '../utils/formatting.dart';
import '../utils/i18n.dart';

/// Transaction data for display
class TransactionDisplay {
  final String date;
  final String category;
  final String type;
  final String split;
  final int amount;
  final String amountFormatted;
  final String description;
  final String payer;

  TransactionDisplay({
    required this.date,
    required this.category,
    required this.type,
    required this.split,
    required this.amount,
    required this.amountFormatted,
    required this.description,
    required this.payer,
  });
}

/// Period summary data structure
class PeriodSummaryData {
  final int periodId;
  final String periodName;
  final DateTime startDate;
  final DateTime? endDate;
  final bool isSettled;
  final DateTime? settledDate;
  final List<TransactionDisplay> transactions;
  final int deposits;
  final String depositsFormatted;
  final int expenses;
  final String expensesFormatted;
  final int publicFundBalance;
  final List<({String name, int balance, bool paidRemainder})> memberBalances;

  PeriodSummaryData({
    required this.periodId,
    required this.periodName,
    required this.startDate,
    this.endDate,
    required this.isSettled,
    this.settledDate,
    required this.transactions,
    required this.deposits,
    required this.depositsFormatted,
    required this.expenses,
    required this.expensesFormatted,
    required this.publicFundBalance,
    required this.memberBalances,
  });
}

/// Display a period view with transactions and balances.
void displayViewPeriod(PeriodSummaryData summary) {
  final period = summary;

  // Format dates
  final startDateStr = _formatDate(period.startDate);
  final depositsFormatted = '+${period.depositsFormatted}';
  final expensesFormatted = '-${period.expensesFormatted}';
  final fundFormatted = centsToDollars(period.publicFundBalance.abs());
  final fundSign = period.publicFundBalance >= 0 ? '+' : '-';

  // Print period header
  print('\n${'=' * 60}');
  print('                 ${period.periodName}');
  print('=' * 60);

  // Print period status
  if (period.isSettled && period.settledDate != null) {
    final settledDateStr = _formatDate(period.settledDate!);
    print(
      translate('Started: {} | Settled: {}', [startDateStr, settledDateStr]),
    );
  } else if (period.isSettled && period.endDate != null) {
    final endDateStr = _formatDate(period.endDate!);
    print(translate('Started: {} | Settled: {}', [startDateStr, endDateStr]));
  } else {
    print(translate('Started: {} | Active', [startDateStr]));
  }

  print(
    translate('Deposits: {} | Expenses: {} | Fund: {}{}', [
      depositsFormatted,
      expensesFormatted,
      fundSign,
      fundFormatted,
    ]),
  );

  // Display transactions
  if (period.transactions.isNotEmpty) {
    print(
      translate('\n--- Transactions ({}) ---', [period.transactions.length]),
    );
    _displayTransactionTable(period.transactions);
  } else {
    print(translate('\n--- Transactions (0) ---'));
    print(translate('  No transactions in this period.'));
  }

  // Display member balances
  if (period.memberBalances.isNotEmpty) {
    print(
      translate('\n--- Balances ({} active) ---', [
        period.memberBalances.length,
      ]),
    );
    final memberStrings = period.memberBalances.map((member) {
      final balanceFormatted = centsToDollars(member.balance.abs());
      final balanceSign = member.balance >= 0 ? '+' : '-';
      final remainderStr = member.paidRemainder ? '✓' : '✗';
      return '${member.name} $remainderStr $balanceSign\$$balanceFormatted';
    }).toList();
    print('  ${memberStrings.join(' | ')}');
  } else {
    print(translate('\n--- Balances (0 active) ---'));
    print(translate('  No active members.'));
  }

  print('\n${'=' * 60}\n');
}

/// Display settlement plan transactions.
void displaySettlementPlan(List<TransactionDisplay> transactions) {
  if (transactions.isEmpty) {
    print(
      translate(
        'No settlement transactions needed (all balances already zero).',
      ),
    );
    return;
  }

  print(translate('\n--- Settlement Plan ---'));
  _displayTransactionTable(transactions);
  print(translate('----------------------\n'));
}

/// Display a formatted transaction table.
void _displayTransactionTable(List<TransactionDisplay> transactions) {
  // Calculate column widths using display width
  var maxCategoryWidth = transactions
      .map((t) => getDisplayWidth(t.category))
      .fold(0, (a, b) => a > b ? a : b);
  var maxDescWidth = transactions
      .map((t) => getDisplayWidth(t.description))
      .fold(0, (a, b) => a > b ? a : b);
  var maxPayerWidth = transactions
      .map((t) => getDisplayWidth(t.payer))
      .fold(0, (a, b) => a > b ? a : b);
  var maxSplitWidth = transactions
      .map((t) => getDisplayWidth(t.split))
      .fold(0, (a, b) => a > b ? a : b);

  // Use display width for headers too
  final headerDate = translate('Date');
  final headerCategory = translate('Category');
  final headerType = translate('Type');
  final headerSplit = translate('Split');
  final headerAmount = translate('Amount');
  final headerDescription = translate('Description');
  final headerFromTo = translate('From/To');

  var categoryWidth = maxCategoryWidth > getDisplayWidth(headerCategory)
      ? maxCategoryWidth
      : getDisplayWidth(headerCategory);
  var descWidth = maxDescWidth > getDisplayWidth(headerDescription)
      ? maxDescWidth
      : getDisplayWidth(headerDescription);
  var payerWidth = maxPayerWidth > getDisplayWidth(headerFromTo)
      ? maxPayerWidth
      : getDisplayWidth(headerFromTo);
  var splitWidth = maxSplitWidth > getDisplayWidth(headerSplit)
      ? maxSplitWidth
      : getDisplayWidth(headerSplit);

  // Ensure minimum widths
  categoryWidth = categoryWidth > 15 ? categoryWidth : 15;
  descWidth = descWidth > 20 ? descWidth : 20;
  payerWidth = payerWidth > 12 ? payerWidth : 12;
  splitWidth = splitWidth > 10 ? splitWidth : 10;

  // Print header
  final headerLine =
      '  ${padToDisplayWidth(headerDate, 12)} | '
      '${padToDisplayWidth(headerCategory, categoryWidth)} | '
      '${padToDisplayWidth(headerType, 8)} | '
      '${padToDisplayWidth(headerSplit, splitWidth)} | '
      '${padToDisplayWidth(headerAmount, 12, '>')} | '
      '${padToDisplayWidth(headerDescription, descWidth)} | '
      '${padToDisplayWidth(headerFromTo, payerWidth)}';
  print(headerLine);
  print(
    '  ${'-' * 12} | ${'-' * categoryWidth} | ${'-' * 8} | '
    '${'-' * splitWidth} | ${'-' * 12} | ${'-' * descWidth} | '
    '${'-' * payerWidth}',
  );

  // Print transactions
  for (final tx in transactions) {
    final descDisplay = tx.description;
    final txLine =
        '  ${padToDisplayWidth(tx.date, 12)} | '
        '${padToDisplayWidth(tx.category, categoryWidth)} | '
        '${padToDisplayWidth(tx.type, 8)} | '
        '${padToDisplayWidth(tx.split, splitWidth)} | '
        '${padToDisplayWidth(tx.amountFormatted, 12, '>')} | '
        '${padToDisplayWidth(descDisplay, descWidth)} | '
        '${padToDisplayWidth(tx.payer, payerWidth)}';
    print(txLine);
  }
}

/// Format a DateTime to YYYY-MM-DD string.
String _formatDate(DateTime date) {
  return '${date.year}-${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';
}
