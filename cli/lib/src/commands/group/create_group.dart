// Create group command.

import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Create group command.
class CreateGroupCommand extends Command {
  @override
  String get description => translate('Create Group');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<void> execute(CommandContext context) async {
    final name = promptString(translate('Group Name: '));
    if (name == null || name.isEmpty) {
      print(translate('Group creation cancelled.'));
      return;
    }

    final group = await context.groupService.createGroup(name);
    if (group != null) {
      print(translate('Group created successfully.'));
      context.session.setGroup(group.id, group.name);

      // Automatically select the current active period for this group (if any)
      final currentPeriod = await context.groupService.getCurrentPeriod(group.id);
      if (currentPeriod != null) {
        context.session.setPeriod(currentPeriod.id, currentPeriod.name);
        print(translate('Period selected: {}', [currentPeriod.name]));
      }

      // Save to preferences
      context.config.preferences.setLastActiveGroup(context.session.currentGroupId!);
      await context.config.preferences.save();
    } else {
      print(translate('Failed to create group.'));
    }
  }
}
