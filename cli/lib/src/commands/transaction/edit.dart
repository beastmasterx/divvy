// Edit transaction command (draft only).

import '../../models/session.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Edit transaction command (draft only).
class EditTransactionCommand extends Command {
  @override
  String get description => translate('Edit (draft only)');

  @override
  bool canExecute(Session session) =>
      session.isAuthenticated &&
      session.currentGroupId != null &&
      session.currentPeriodId != null &&
      session.currentTransactionId != null;

  @override
  Future<void> execute(CommandContext context) async {
    if (context.session.currentTransactionId == null) {
      print(translate('No transaction selected.'));
      return;
    }

    final transaction = await context.transactionService.getTransaction(context.session.currentTransactionId!);
    if (transaction == null) {
      print(translate('Transaction not found.'));
      return;
    }

    // Check if transaction is in draft status
    if (transaction.status.toString().split('.').last != 'draft') {
      print(translate('Only draft transactions can be edited.'));
      return;
    }

    // TODO: Implement full edit flow as guided flow
    // For now, just show a message
    print(translate('Transaction editing flow not yet implemented.'));
    print(translate('Current transaction: ID {}', [transaction.id]));
  }
}
