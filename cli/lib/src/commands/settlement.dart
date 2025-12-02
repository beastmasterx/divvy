// Settlement management commands.

import '../models/session.dart';
import '../services/period.dart';
import '../ui/prompts.dart';
import '../ui/tables.dart';
import '../utils/i18n.dart';

/// Handle view balances command.
Future<void> handleViewBalances(
  PeriodService periodService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
    print(translate('No period selected.'));
    return;
  }

  final balances = await periodService.getBalances(session.currentPeriodId!);
  if (balances.isEmpty) {
    print(translate('No balances available.'));
    return;
  }

  displayTable(
    headers: ['Email', 'Balance'],
    rows: balances.map((b) => [
      b.userEmail ?? b.userId.toString(),
      formatAmount(b.balance),
    ]).toList(),
  );
}

/// Handle view settlement plan command with apply prompt.
Future<void> handleViewSettlementPlan(
  PeriodService periodService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
    print(translate('No period selected.'));
    return;
  }

  // Step 1: Check period status
  final period = await periodService.getPeriod(session.currentPeriodId!);
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

    final closedPeriod = await periodService.closePeriod(session.currentPeriodId!);
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
  final plan = await periodService.getSettlementPlan(session.currentPeriodId!);
  if (plan.isEmpty) {
    print(translate('No settlement needed - all balances are zero.'));
    return;
  }

  print('\n${translate('Settlement Plan')}:');
  displayTable(
    headers: ['Payer', 'Payee', 'Amount'],
    rows: plan.map((s) => [
      s.payerName,
      s.payeeName,
      formatAmount(s.amount),
    ]).toList(),
  );
  print('');

  // Step 3: Apply prompt
  final confirmApply = promptYesNo(translate('Apply settlement plan?'), defaultYes: false);
  if (!confirmApply) {
    print(translate('Settlement plan not applied.'));
    return;
  }

  // Step 4: Apply settlement
  final success = await periodService.applySettlementPlan(session.currentPeriodId!);
  if (success) {
    print(translate('Settlement plan applied successfully.'));
    print(translate('Period is now settled.'));
  } else {
    print(translate('Failed to apply settlement plan.'));
  }
}

/// Handle apply settlement command.
Future<void> handleApplySettlement(
  PeriodService periodService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
    print(translate('No period selected.'));
    return;
  }

  // Show settlement plan first
  await handleViewSettlementPlan(periodService, session);

  final confirm = promptYesNo(translate('Apply settlement plan?'));
  if (!confirm) {
    print(translate('Settlement cancelled.'));
    return;
  }

  final success = await periodService.applySettlementPlan(session.currentPeriodId!);
  if (success) {
    print(translate('Settlement plan applied successfully.'));
  } else {
    print(translate('Failed to apply settlement plan.'));
  }
}

