// Get group command (list or get specific group).

import '../../api/schemas.dart';
import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../tables.dart';

/// Get group command - lists groups or gets a specific group.
class GetGroupCommand extends Command {
  @override
  String get description => translate('Get Group');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      // If name/ID provided, get specific group
      if (args != null && args.isNotEmpty) {
        final identifier = args[0];

        // Try as ID first
        final id = int.tryParse(identifier);
        if (id != null) {
          final group = await context.groupService.getGroup(id);
          if (group != null) {
            _printGroup(group);
            return 0;
          } else {
            print(translate('Group not found.'));
            return 1;
          }
        }

        // Try as name
        final groups = await context.groupService.listGroups();
        final matchingGroups = groups.where((g) => g.name.toLowerCase() == identifier.toLowerCase()).toList();

        if (matchingGroups.isEmpty) {
          print(translate('Group not found.'));
          return 1;
        }

        if (matchingGroups.length > 1) {
          print(translate('Multiple groups found with that name.'));
          return 1;
        }

        _printGroup(matchingGroups.first);
        return 0;
      }

      // No identifier - list all groups
      final groups = await context.groupService.listGroups();
      if (groups.isEmpty) {
        print(translate('No groups available.'));
        return 0;
      }

      // Display groups in a table
      displayTable(headers: ['ID', 'Name'], rows: groups.map((g) => [g.id.toString(), g.name]).toList());

      return 0;
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }

  void _printGroup(GroupResponse group) {
    print('ID: ${group.id}');
    print('Name: ${group.name}');
  }
}
