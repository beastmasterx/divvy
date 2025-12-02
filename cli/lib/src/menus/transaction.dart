// Transaction menu (period level).

import '../commands/commands.dart';
import '../commands/menu.dart';

/// Menu shown at period level (group and period selected).
class TransactionMenu extends Menu {
  TransactionMenu() : super([ViewTransactionsCommand(), ViewBalancesCommand(), MoreCommand(), ExitCommand()]);
}

/// "More" menu shown at period level.
class TransactionMoreMenu extends Menu {
  TransactionMoreMenu()
    : super([
        SelectTransactionCommand(),
        AddTransactionCommand(),
        ViewSettlementPlanCommand(),
        SettingsCommand(),
        LogoutCommand(),
        BackToTopCommand(),
        ExitCommand(),
      ]);
}
