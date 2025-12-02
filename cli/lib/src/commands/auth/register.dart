// Register command.

import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Register command.
class RegisterCommand extends Command {
  @override
  String get description => translate('Register');

  @override
  bool canExecute(Session session) => !session.isAuthenticated;

  @override
  Future<void> execute(CommandContext context) async {
    try {
      final email = promptEmail();
      if (email == null) {
        print(translate('Registration cancelled.'));
        return;
      }

      final name = promptString(translate('Name: '));
      if (name == null) {
        print(translate('Registration cancelled.'));
        return;
      }

      final password = promptPassword();
      if (password == null) {
        print(translate('Registration cancelled.'));
        return;
      }

      print(translate('Registering...'));
      final success = await context.auth.register(email, name, password);
      if (success) {
        print(translate('Registration successful!'));
        context.session.isAuthenticated = true;
        // Fetch and set user info
        final user = await context.userService.getCurrentUser();
        if (user != null) {
          context.session.setUser(user.name, user.email);
        }
      } else {
        print(translate('Email already exists.'));
      }
    } catch (e) {
      ensureTerminalState();
      rethrow;
    }
  }
}
