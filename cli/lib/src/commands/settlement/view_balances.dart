// View balances command.

import '../../models/session.dart';
import '../../ui/tables.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// View balances command.
class ViewBalancesCommand extends Command {
  @override
  String get description => translate('View Balances');

  @override
  bool canExecute(Session session) =>
      session.isAuthenticated && session.currentGroupId != null && session.currentPeriodId != null;

  @override
  Future<void> execute(CommandContext context) async {
    if (context.session.currentPeriodId == null) {
      print(translate('No period selected.'));
      return;
    }

    final balances = await context.periodService.getBalances(context.session.currentPeriodId!);
    if (balances.isEmpty) {
      print(translate('No balances available.'));
      return;
    }

    displayTable(
      headers: ['Email', 'Balance'],
      rows: balances.map((b) => [b.userEmail ?? b.userId.toString(), formatAmount(b.balance)]).toList(),
    );
  }
}
