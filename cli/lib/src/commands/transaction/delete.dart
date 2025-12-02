// Delete transaction command (draft only).

import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Delete transaction command (draft only).
class DeleteTransactionCommand extends Command {
  @override
  String get description => translate('Delete (draft only)');

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
      print(translate('Only draft transactions can be deleted.'));
      return;
    }

    final confirm = promptYesNo(translate('Delete this transaction?'), defaultYes: false);
    if (!confirm) {
      print(translate('Deletion cancelled.'));
      return;
    }

    final success = await context.transactionService.deleteTransaction(context.session.currentTransactionId!);
    if (success) {
      print(translate('Transaction deleted successfully.'));
      context.session.currentTransactionId = null;
      context.session.currentTransactionDescription = null;
    } else {
      print(translate('Failed to delete transaction.'));
    }
  }
}
