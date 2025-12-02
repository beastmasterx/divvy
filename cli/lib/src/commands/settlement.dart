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
    headers: ['User ID', 'Balance'],
    rows: balances.map((b) => [
      b.userId.toString(),
      formatAmount(b.balance),
    ]).toList(),
  );
}

/// Handle view settlement plan command.
Future<void> handleViewSettlementPlan(
  PeriodService periodService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
    print(translate('No period selected.'));
    return;
  }

  final plan = await periodService.getSettlementPlan(session.currentPeriodId!);
  if (plan.isEmpty) {
    print(translate('No settlement needed.'));
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

