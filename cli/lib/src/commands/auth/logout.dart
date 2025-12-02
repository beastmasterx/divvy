// Logout command.

import '../../models/session.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Logout command.
class LogoutCommand extends Command {
  @override
  String get description => translate('Logout');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<void> execute(CommandContext context) async {
    await context.auth.logout();
    context.session.clear();
    print(translate('Logged out successfully.'));
  }
}
