// Group management commands.

import '../models/session.dart';
import '../services/group.dart';
import '../ui/prompts.dart';
import '../ui/tables.dart';
import '../utils/i18n.dart';
import 'package:divvy_api_client/divvy_api_client.dart';

/// Handle select group command.
Future<void> handleSelectGroup(
  GroupService groupService,
  Session session,
) async {
  final groups = await groupService.listGroups();
  if (groups.isEmpty) {
    print(translate('No groups available.'));
    return;
  }

  displayList<GroupResponse>(
    items: groups,
    itemToString: (g) => g.name,
    header: translate('Select a group:'),
  );

  final choice = promptSelection('', groups.length);
  if (choice == null) {
    print(translate('Selection cancelled.'));
    return;
  }

  final selectedGroup = groups[choice - 1];
  session.setGroup(selectedGroup.id, selectedGroup.name);
  print(translate('Group selected: {}', [selectedGroup.name]));
}

/// Handle create group command.
Future<void> handleCreateGroup(
  GroupService groupService,
  Session session,
) async {
  final name = promptString(translate('Group Name: '));
  if (name == null || name.isEmpty) {
    print(translate('Group creation cancelled.'));
    return;
  }

  final group = await groupService.createGroup(name);
  if (group != null) {
    print(translate('Group created successfully.'));
    session.setGroup(group.id, group.name);
  } else {
    print(translate('Failed to create group.'));
  }
}

