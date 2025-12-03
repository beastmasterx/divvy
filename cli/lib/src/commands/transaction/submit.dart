// Submit transaction command (draft only).

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../prompts.dart';

/// Submit transaction command (draft only).
class SubmitTransactionCommand extends Command {
  @override
  String get description => translate('Submit Transaction');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      int? transactionId;

      if (args != null && args.isNotEmpty) {
        final identifier = args[0];
        final id = int.tryParse(identifier);
        if (id != null) {
          transactionId = id;
        } else {
          print(translate('Invalid transaction ID: {}', [identifier]));
          return 1;
        }
      } else {
        transactionId = context.session.currentTransactionId;
      }

      if (transactionId == null) {
        print(translate('No transaction ID specified or selected.'));
        return 1;
      }

      final transaction = await context.transactionService.getTransaction(transactionId);
      if (transaction == null) {
        print(translate('Transaction not found.'));
        return 1;
      }

      // Check if transaction is in draft status
      if (transaction.status.toString() != 'TransactionStatus.draft') {
        print(translate('Only draft transactions can be submitted.'));
        return 1;
      }

      final confirm = promptYesNo(translate('Submit this transaction for approval?'), defaultYes: false);
      if (!confirm) {
        print(translate('Submission cancelled.'));
        return 1;
      }

      final updatedTransaction = await context.transactionService.submitTransaction(transactionId);
      if (updatedTransaction != null) {
        print(translate('Transaction submitted successfully.'));
        return 0;
      } else {
        print(translate('Failed to submit transaction.'));
        return 1;
      }
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
