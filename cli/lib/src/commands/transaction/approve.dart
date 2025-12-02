// Approve transaction command.

import '../../models/session.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Approve transaction command.
class ApproveTransactionCommand extends Command {
  @override
  String get description => translate('Approve');

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

    final transaction = await context.transactionService.approveTransaction(context.session.currentTransactionId!);
    if (transaction != null) {
      print(translate('Transaction approved successfully.'));
    } else {
      print(translate('Failed to approve transaction.'));
    }
  }
}
