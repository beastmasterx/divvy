// Submit transaction command (draft only).

import '../../api/schemas.dart';
import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Submit transaction command (draft only).
class SubmitTransactionCommand extends Command {
  @override
  String get description => translate('Submit (draft only)');

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
    if (transaction.status != TransactionStatus.draft) {
      print(translate('Only draft transactions can be submitted.'));
      return;
    }

    final confirm = promptYesNo(translate('Submit this transaction for approval?'), defaultYes: false);
    if (!confirm) {
      print(translate('Submission cancelled.'));
      return;
    }

    final updatedTransaction = await context.transactionService.submitTransaction(
      context.session.currentTransactionId!,
    );
    if (updatedTransaction != null) {
      print(translate('Transaction submitted successfully.'));
    } else {
      print(translate('Failed to submit transaction.'));
    }
  }
}
