// Transaction detail menu (transaction level).

import '../commands/commands.dart';
import '../commands/menu.dart';

/// Menu shown at transaction level (group, period, and transaction selected).
class TransactionDetailMenu extends Menu {
  TransactionDetailMenu()
    : super([
        ViewTransactionDetailsCommand(),
        ApproveTransactionCommand(),
        RejectTransactionCommand(),
        EditTransactionCommand(),
        BackToTransactionsCommand(),
        MoreCommand(),
        ExitCommand(),
      ]);
}

/// "More" menu shown at transaction level.
class TransactionDetailMoreMenu extends Menu {
  TransactionDetailMoreMenu()
    : super([
        DeleteTransactionCommand(),
        SubmitTransactionCommand(),
        SettingsCommand(),
        LogoutCommand(),
        BackToTopCommand(),
        ExitCommand(),
      ]);
}
