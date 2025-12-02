// Select group command.

import 'package:divvy_api_client/divvy_api_client.dart';

import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../ui/tables.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Select group command.
class SelectGroupCommand extends Command {
  @override
  String get description => translate('Select Group');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<void> execute(CommandContext context) async {
    final groups = await context.groupService.listGroups();
    if (groups.isEmpty) {
      print(translate('No groups available.'));
      return;
    }

    displayList<GroupResponse>(items: groups, itemToString: (g) => g.name, header: translate('Select a group:'));

    final choice = promptSelection('', groups.length);
    if (choice == null) {
      print(translate('Selection cancelled.'));
      return;
    }

    final selectedGroup = groups[choice - 1];
    context.session.setGroup(selectedGroup.id, selectedGroup.name);
    print(translate('Group selected: {}', [selectedGroup.name]));

    // Automatically select the current active period for this group
    final currentPeriod = await context.groupService.getCurrentPeriod(selectedGroup.id);
    if (currentPeriod != null) {
      context.session.setPeriod(currentPeriod.id, currentPeriod.name);
      print(translate('Period selected: {}', [currentPeriod.name]));
    }

    // Save to preferences
    if (context.session.currentGroupId != null) {
      context.config.preferences.setLastActiveGroup(context.session.currentGroupId!);
      await context.config.preferences.save();
    }
  }
}
