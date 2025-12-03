// Reject transaction command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Reject transaction command.
class RejectTransactionCommand extends Command {
  @override
  String get description => translate('Reject Transaction');

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

      final transaction = await context.transactionService.rejectTransaction(transactionId);
      if (transaction != null) {
        print(translate('Transaction rejected successfully.'));
        return 0;
      } else {
        print(translate('Failed to reject transaction.'));
        return 1;
      }
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
