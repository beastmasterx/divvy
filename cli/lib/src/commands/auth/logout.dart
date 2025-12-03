// Logout command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Logout command.
class LogoutCommand extends Command {
  // No mixin needed - doesn't parse arguments
  @override
  String get description => translate('Logout');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      await context.auth.logout();
      context.session.clear();
      print(translate('Logged out successfully.'));
      return 0;
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
