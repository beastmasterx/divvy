// Select transaction command.

import '../../api/schemas.dart';
import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../ui/tables.dart';
import '../../utils/formatting.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Select transaction command.
class SelectTransactionCommand extends Command {
  @override
  String get description => translate('Select Transaction');

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

    displayList<TransactionResponse>(
      items: transactions,
      itemToString: (t) =>
          'ID ${t.id}: ${formatAmount(t.amount)} - ${t.description ?? translate('No description')} (${getEnumName(t.status)})',
      header: translate('Select a transaction:'),
    );

    final choice = promptSelection('', transactions.length);
    if (choice == null) {
      print(translate('Selection cancelled.'));
      return;
    }

    final selectedTransaction = transactions[choice - 1];
    context.session.setTransaction(selectedTransaction.id, selectedTransaction.description);
    print(translate('Transaction selected: ID {}', [selectedTransaction.id]));
  }
}
