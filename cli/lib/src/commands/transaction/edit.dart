// Edit transaction command (draft only).

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Edit transaction command (draft only).
class EditTransactionCommand extends Command {
  @override
  String get description => translate('Edit Transaction');

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
        print(translate('Only draft transactions can be edited.'));
        return 1;
      }

      // TODO: Implement full edit flow as guided flow
      // For now, just show a message
      print(translate('Transaction editing flow not yet implemented.'));
      print(translate('Current transaction: ID {}', [transaction.id]));
      return 0;
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
