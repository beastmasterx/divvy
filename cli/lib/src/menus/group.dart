// Group menu (authenticated, no group selected).

import '../commands/commands.dart';
import '../commands/menu.dart';

/// Menu shown when authenticated but no group is selected.
class GroupMenu extends Menu {
  GroupMenu() : super([SelectGroupCommand(), CreateGroupCommand(), MoreCommand(), ExitCommand()]);
}

/// "More" menu shown when no group is selected.
class GroupMoreMenu extends Menu {
  GroupMoreMenu() : super([SettingsCommand(), LogoutCommand(), BackToTopCommand(), ExitCommand()]);
}
