// User menu (unauthenticated).

import '../commands/commands.dart';
import '../commands/menu.dart';

/// Menu shown when user is not authenticated.
class UserMenu extends Menu {
  UserMenu() : super([LoginCommand(), RegisterCommand(), ExitCommand()]);
}
