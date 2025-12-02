// Period management commands.

import '../api/client.dart';
import '../models/session.dart';
import '../services/period.dart';
import '../ui/prompts.dart';
import '../utils/i18n.dart';
import 'package:divvy_api_client/divvy_api_client.dart';

/// Handle view period command.
Future<void> handleViewPeriod(
  PeriodService periodService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
    print(translate('No period selected.'));
    return;
  }

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

