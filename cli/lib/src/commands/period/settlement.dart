// Get settlement plan and optionally apply it command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../prompts.dart';
import '../tables.dart';

/// Settlement command - shows settlement plan and optionally applies it.
class SettlementCommand extends Command {
  @override
  String get description => translate('Settlement');

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

      // Verify period exists
      final period = await context.periodService.getPeriod(periodId);
      if (period == null) {
        print(translate('Period not found.'));
        return 1;
      }

      // Get settlement plan
      final plan = await context.periodService.getSettlementPlan(periodId);
      if (plan.isEmpty) {
        print(translate('No settlement needed - all balances are zero.'));
        return 0;
      }

      print('\n${translate('Settlement Plan')}:');
      displayTable(
        headers: ['Payer', 'Payee', 'Amount'],
        rows: plan.map((s) => [s.payerName, s.payeeName, formatAmount(s.amount)]).toList(),
      );
      print('');

      // Check if --apply flag is present
      final shouldApply = args != null && args.contains('--apply');

      if (shouldApply) {
        // Check period status before applying
        final currentPeriod = await context.periodService.getPeriod(periodId);
        if (currentPeriod == null) {
          print(translate('Period not found.'));
          return 1;
        }

        if (currentPeriod.status.toString() == 'PeriodStatus.open') {
          print(translate('The period must be closed before applying the settlement plan.'));
          final confirmClose = promptYesNo(translate('Close this period?'), defaultYes: false);
          if (!confirmClose) {
            print(translate('Settlement plan application cancelled.'));
            return 1;
          }

          final closedPeriod = await context.periodService.closePeriod(periodId);
          if (closedPeriod == null) {
            print(translate('Failed to close period.'));
            return 1;
          }
          print(translate('Period closed successfully.'));
          print('');
        } else if (currentPeriod.status.toString() == 'PeriodStatus.settled') {
          print(translate('This period is already settled.'));
          return 0;
        }

        // Apply settlement
        final success = await context.periodService.applySettlementPlan(periodId);
        if (success) {
          print(translate('Settlement plan applied successfully.'));
          print(translate('Period is now settled.'));
          return 0;
        } else {
          print(translate('Failed to apply settlement plan.'));
          return 1;
        }
      } else {
        // Just show the plan, optionally prompt to apply
        final confirmApply = promptYesNo(translate('Apply settlement plan?'), defaultYes: false);
        if (!confirmApply) {
          print(translate('Settlement plan not applied.'));
          return 0;
        }

        // Check period status before applying
        final currentPeriod = await context.periodService.getPeriod(periodId);
        if (currentPeriod == null) {
          print(translate('Period not found.'));
          return 1;
        }

        if (currentPeriod.status.toString() == 'PeriodStatus.open') {
          print(translate('The period must be closed before applying the settlement plan.'));
          final confirmClose = promptYesNo(translate('Close this period?'), defaultYes: false);
          if (!confirmClose) {
            print(translate('Settlement plan application cancelled.'));
            return 1;
          }

          final closedPeriod = await context.periodService.closePeriod(periodId);
          if (closedPeriod == null) {
            print(translate('Failed to close period.'));
            return 1;
          }
          print(translate('Period closed successfully.'));
          print('');
        } else if (currentPeriod.status.toString() == 'PeriodStatus.settled') {
          print(translate('This period is already settled.'));
          return 0;
        }

        // Apply settlement
        final success = await context.periodService.applySettlementPlan(periodId);
        if (success) {
          print(translate('Settlement plan applied successfully.'));
          print(translate('Period is now settled.'));
          return 0;
        } else {
          print(translate('Failed to apply settlement plan.'));
          return 1;
        }
      }
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
