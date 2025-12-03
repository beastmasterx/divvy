// Status command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Status command to show authentication status.
class StatusCommand extends Command {
  // No mixin needed - doesn't parse arguments
  @override
  String get description => translate('Status');

  @override
  bool canExecute(Session session) => true; // Always available

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    if (context.auth.isAuthenticated) {
      try {
        final user = await context.userService.getCurrentUser();
        if (user != null) {
          print('Authenticated as: ${user.email} (${user.name})');
          return 0;
        } else {
          print('Authenticated but unable to fetch user info.');
          return 1;
        }
      } catch (e) {
        print('Error fetching user info: ${formatApiError(e)}');
        return 1;
      }
    } else {
      print('Not authenticated.');
      return 1;
    }
  }
}
