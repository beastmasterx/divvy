// View transactions command.

import '../../models/session.dart';
import '../../ui/tables.dart';
import '../../utils/formatting.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// View transactions command.
class ViewTransactionsCommand extends Command {
  @override
  String get description => translate('View Transactions');

  @override
  bool canExecute(Session session) =>
      session.isAuthenticated && session.currentGroupId != null && session.currentPeriodId != null;

  @override
  Future<void> execute(CommandContext context) async {
    if (context.session.currentPeriodId == null) {
      print(translate('No period selected.'));
      return;
    }

    final transactions = await context.periodService.getTransactions(context.session.currentPeriodId!);
    if (transactions.isEmpty) {
      print(translate('No transactions available.'));
      return;
    }

    displayTable(
      headers: ['ID', 'Type', 'Amount', 'Description', 'Status'],
      rows: transactions
          .map(
            (t) => [
              t.id.toString(),
              getEnumName(t.transactionKind),
              formatAmount(t.amount),
              t.description ?? '',
              getEnumName(t.status),
            ],
          )
          .toList(),
    );
  }
}
