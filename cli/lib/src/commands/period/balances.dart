// Get balances for a period command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../tables.dart';

/// Get balances command - shows balances for a period.
class GetBalancesCommand extends Command {
  @override
  String get description => translate('Get Balances');

  @override
  bool canExecute(Session session) => session.isAuthenticated && session.currentPeriodId != null;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      // Use period from args if provided, otherwise use current period
      int? periodId = context.session.currentPeriodId;

      if (args != null && args.isNotEmpty) {
        final identifier = args[0];
        final id = int.tryParse(identifier);
        if (id != null) {
          periodId = id;
        } else {
          // Try to find by name
          if (context.session.currentGroupId == null) {
            print(translate('No group selected.'));
            return 1;
          }
          final periods = await context.periodService.getPeriodsByGroup(context.session.currentGroupId!);
          final matching = periods.where((p) => p.name.toLowerCase() == identifier.toLowerCase()).toList();
          if (matching.isEmpty) {
            print(translate('Period not found.'));
            return 1;
          }
          if (matching.length > 1) {
            print(translate('Multiple periods found with that name.'));
            return 1;
          }
          periodId = matching.first.id;
        }
      }

      if (periodId == null) {
        print(translate('No period specified or selected.'));
        return 1;
      }

      final balances = await context.periodService.getBalances(periodId);
      if (balances.isEmpty) {
        print(translate('No balances available.'));
        return 0;
      }

      displayTable(
        headers: ['Email', 'Balance'],
        rows: balances.map((b) => [b.userEmail ?? b.userId.toString(), formatAmount(b.balance)]).toList(),
      );

      return 0;
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
