// Login command.

import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Login command.
class LoginCommand extends Command {
  @override
  String get description => translate('Login');

  @override
  bool canExecute(Session session) => !session.isAuthenticated;

  @override
  Future<void> execute(CommandContext context) async {
    try {
      final email = promptEmail();
      if (email == null) {
        print(translate('Login cancelled.'));
        return;
      }

      final password = promptPassword();
      if (password == null) {
        print(translate('Login cancelled.'));
        return;
      }

      print(translate('Logging in...'));
      final success = await context.auth.login(email, password);
      if (success) {
        print(translate('Login successful!'));
        context.session.isAuthenticated = true;
        // Fetch and set user info
        final user = await context.userService.getCurrentUser();
        if (user != null) {
          context.session.setUser(user.name, user.email);
        }
      } else {
        print(translate('Invalid credentials.'));
      }
    } catch (e) {
      ensureTerminalState();
      rethrow;
    }
  }
}
