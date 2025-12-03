// Login command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../option_parser.dart';
import '../prompts.dart';

/// Login command.
class LoginCommand extends Command with OptionParserMixin {
  @override
  String get description => translate('Login');

  @override
  bool canExecute(Session session) => !session.isAuthenticated;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      // Parse and prompt in one call - much cleaner!
      final email = parseOption(args, longName: 'user', shortName: 'u', prompt: promptEmail);
      if (email == null) {
        print(translate('Login cancelled.'));
        return 1;
      }

      final password = parseOption(args, longName: 'password', shortName: 'p', prompt: promptPassword);
      if (password == null) {
        print(translate('Login cancelled.'));
        return 1;
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
        return 0;
      } else {
        print(translate('Invalid credentials.'));
        return 1;
      }
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
