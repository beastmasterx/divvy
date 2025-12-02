// View settlement plan command.

import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../ui/tables.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// View settlement plan command.
class ViewSettlementPlanCommand extends Command {
  @override
  String get description => translate('View Settlement Plan');

  @override
  bool canExecute(Session session) =>
      session.isAuthenticated && session.currentGroupId != null && session.currentPeriodId != null;

  @override
  Future<void> execute(CommandContext context) async {
    if (context.session.currentPeriodId == null) {
      print(translate('No period selected.'));
      return;
    }

    // Step 1: Check period status
    final period = await context.periodService.getPeriod(context.session.currentPeriodId!);
    if (period == null) {
      print(translate('Period not found.'));
      return;
    }

    // If period is open, prompt to close it first
    if (period.status.toString().split('.').last == 'open') {
      print(translate('The period must be closed before viewing the settlement plan.'));
      final confirmClose = promptYesNo(translate('Close this period?'), defaultYes: false);
      if (!confirmClose) {
        print(translate('Settlement plan view cancelled.'));
        return;
      }

      final closedPeriod = await context.periodService.closePeriod(context.session.currentPeriodId!);
      if (closedPeriod == null) {
        print(translate('Failed to close period.'));
        return;
      }
      print(translate('Period closed successfully.'));
      print('');
    } else if (period.status.toString().split('.').last == 'settled') {
      print(translate('This period is already settled.'));
      return;
    }

    // Step 2: View settlement plan
    final plan = await context.periodService.getSettlementPlan(context.session.currentPeriodId!);
    if (plan.isEmpty) {
      print(translate('No settlement needed - all balances are zero.'));
      return;
    }

    print('\n${translate('Settlement Plan')}:');
    displayTable(
      headers: ['Payer', 'Payee', 'Amount'],
      rows: plan.map((s) => [s.payerName, s.payeeName, formatAmount(s.amount)]).toList(),
    );
    print('');

    // Step 3: Apply prompt
    final confirmApply = promptYesNo(translate('Apply settlement plan?'), defaultYes: false);
    if (!confirmApply) {
      print(translate('Settlement plan not applied.'));
      return;
    }

    // Step 4: Apply settlement
    final success = await context.periodService.applySettlementPlan(context.session.currentPeriodId!);
    if (success) {
      print(translate('Settlement plan applied successfully.'));
      print(translate('Period is now settled.'));
    } else {
      print(translate('Failed to apply settlement plan.'));
    }
  }
}
