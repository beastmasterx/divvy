// Period menu (group selected, no period).

import '../commands/commands.dart';
import '../commands/menu.dart';

/// Menu shown when group is selected but no period is selected.
class PeriodMenu extends Menu {
  PeriodMenu() : super([SelectPeriodCommand(), CreatePeriodCommand(), MoreCommand(), ExitCommand()]);
}

/// "More" menu shown when group is selected but no period.
class PeriodMoreMenu extends Menu {
  PeriodMoreMenu() : super([SettingsCommand(), LogoutCommand(), BackToTopCommand(), ExitCommand()]);
}
