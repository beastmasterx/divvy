// Config view command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Config view command - displays all configuration.
class ConfigViewCommand extends Command {
  @override
  String get description => translate('View Configuration');

  @override
  bool canExecute(Session session) => true;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      ensureTerminalState();

      print('Configuration:');
      print('');
      print('Preferences:');
      print('  apiUrl: ${context.config.apiUrl}');
      print('  language: ${context.config.language}');
      print('  defaultGroupId: ${context.config.defaultGroupId ?? 'not set'}');
      print('  lastActiveGroupId: ${context.config.lastActiveGroupId ?? 'not set'}');
      print('  lastActivePeriodId: ${context.config.lastActivePeriodId ?? 'not set'}');
      print('');

      print('Current Context:');
      if (context.session.isAuthenticated) {
        print('  authenticated: true');
        if (context.session.userName != null) {
          print('  user: ${context.session.userName} (${context.session.userEmail})');
        }
      } else {
        print('  authenticated: false');
      }
      print('  currentGroupId: ${context.session.currentGroupId ?? 'not set'}');
      if (context.session.currentGroupName != null) {
        print('  currentGroupName: ${context.session.currentGroupName}');
      }
      print('  currentPeriodId: ${context.session.currentPeriodId ?? 'not set'}');
      if (context.session.currentPeriodName != null) {
        print('  currentPeriodName: ${context.session.currentPeriodName}');
      }
      print('  currentTransactionId: ${context.session.currentTransactionId ?? 'not set'}');

      return 0;
    } catch (e) {
      ensureTerminalState();
      print('Error: ${formatApiError(e)}');
      return 1;
    }
  }
}
