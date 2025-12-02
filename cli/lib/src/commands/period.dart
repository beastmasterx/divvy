// Period management commands.

import '../api/client.dart';
import '../models/session.dart';
import '../services/period.dart';
import '../ui/prompts.dart';
import '../ui/tables.dart';
import '../utils/i18n.dart';
import 'package:divvy_api_client/divvy_api_client.dart';

/// Handle view period command.
Future<void> handleViewPeriod(
  PeriodService periodService,
  Session session,
) async {
  // If period is already selected, show it
  if (session.currentPeriodId != null) {
    final period = await periodService.getPeriod(session.currentPeriodId!);
    if (period == null) {
      print(translate('Period not found.'));
      return;
    }

    print('\n${translate('Period: {}', [period.name])}');
    print('Status: ${period.status}');
    print('Start: ${period.startDate}');
    if (period.endDate != null) {
      print('End: ${period.endDate}');
    }
    return;
  }

  // If no period selected but group is selected, list periods and let user select
  if (session.currentGroupId != null) {
    final periods = await periodService.getPeriodsByGroup(session.currentGroupId!);
    if (periods.isEmpty) {
      print(translate('No periods available for this group.'));
      return;
    }

    displayList<PeriodResponse>(
      items: periods,
      itemToString: (p) => '${p.name} (${p.status})',
      header: translate('Select a period:'),
    );

    final choice = promptSelection('', periods.length);
    if (choice == null) {
      print(translate('Selection cancelled.'));
      return;
    }

    final selectedPeriod = periods[choice - 1];
    session.setPeriod(selectedPeriod.id, selectedPeriod.name);
    print(translate('Period selected: {}', [selectedPeriod.name]));
    return;
  }

  // No group selected
  print(translate('No group selected.'));
}

/// Handle create period command.
Future<void> handleCreatePeriod(
  DivvyClient client,
  PeriodService periodService,
  Session session,
) async {
  if (session.currentGroupId == null) {
    print(translate('No group selected.'));
    return;
  }

  final name = promptString(translate('Period Name: '));
  if (name == null || name.isEmpty) {
    print(translate('Period creation cancelled.'));
    return;
  }

  try {
    final request = PeriodRequest((b) => b..name = name);
    final response = await client.groups.createPeriodApiV1GroupsGroupIdPeriodsPost(
      groupId: session.currentGroupId!,
      periodRequest: request,
    );

    if (response.data != null) {
      print(translate('Period created successfully.'));
      session.setPeriod(response.data!.id, response.data!.name);
    } else {
      print(translate('Failed to create period.'));
    }
  } catch (e) {
    print(translate('Error: {}', [e.toString()]));
  }
}

/// Handle period settlement flow (close -> view settlement -> apply).
Future<void> handlePeriodSettlementFlow(
  PeriodService periodService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
    print(translate('No period selected.'));
    return;
  }

  // Step 1: Get current period status
  final period = await periodService.getPeriod(session.currentPeriodId!);
  if (period == null) {
    print(translate('Period not found.'));
    return;
  }

  print('\n${translate('Period Settlement Flow')}');
  print('${translate('Period')}: ${period.name}');
  print('${translate('Status')}: ${period.status}');
  print('');

  // Step 2: Close period if it's open
  if (period.status.toString().split('.').last == 'open') {
    print(translate('Step 1: Close Period'));
    print(translate('The period must be closed before settlement can be applied.'));
    final confirmClose = promptYesNo(translate('Close this period?'), defaultYes: false);
    if (!confirmClose) {
      print(translate('Settlement flow cancelled.'));
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

  // Step 3: Show settlement plan
  print(translate('Step 2: Settlement Plan'));
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

  // Step 4: Apply settlement
  print(translate('Step 3: Apply Settlement'));
  print(translate('This will mark the period as settled and record the settlement transactions.'));
  final confirmSettle = promptYesNo(translate('Apply settlement plan?'), defaultYes: false);
  if (!confirmSettle) {
    print(translate('Settlement cancelled.'));
    return;
  }

  final success = await periodService.applySettlementPlan(session.currentPeriodId!);
  if (success) {
    print(translate('Settlement plan applied successfully.'));
    print(translate('Period is now settled.'));
  } else {
    print(translate('Failed to apply settlement plan.'));
  }
}

