// Config current-context command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Config current-context command - displays current context.
class ConfigCurrentContextCommand extends Command {
  @override
  String get description => translate('Current Context');

  @override
  bool canExecute(Session session) => true;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      ensureTerminalState();

      print('Current Context:');
      print('');

      if (context.session.isAuthenticated) {
        if (context.session.userName != null) {
          print('User: ${context.session.userName} (${context.session.userEmail})');
        } else {
          print('User: authenticated');
        }
      } else {
        print('User: not authenticated');
      }

      if (context.session.currentGroupId != null) {
        print('Group: ${context.session.currentGroupName} (ID: ${context.session.currentGroupId})');
      } else {
        print('Group: not set');
      }

      if (context.session.currentPeriodId != null) {
        print('Period: ${context.session.currentPeriodName} (ID: ${context.session.currentPeriodId})');
      } else {
        print('Period: not set');
      }

      if (context.session.currentTransactionId != null) {
        print(
          'Transaction: ${context.session.currentTransactionDescription ?? 'ID: ${context.session.currentTransactionId}'} (ID: ${context.session.currentTransactionId})',
        );
      } else {
        print('Transaction: not set');
      }

      return 0;
    } catch (e) {
      ensureTerminalState();
      print('Error: ${formatApiError(e)}');
      return 1;
    }
  }
}
