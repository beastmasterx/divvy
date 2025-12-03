// Create group command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../option_parser.dart';
import '../prompts.dart';

/// Create group command.
class CreateGroupCommand extends Command with OptionParserMixin {
  @override
  String get description => translate('Create Group');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      // Parse name from args or prompt
      final name = parseOption(
        args,
        longName: 'name',
        shortName: 'n',
        prompt: () => promptString(translate('Group Name: ')),
      );

      if (name == null || name.isEmpty) {
        print(translate('Group creation cancelled.'));
        return 1;
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
        return 0;
      } else {
        print(translate('Failed to create group.'));
        return 1;
      }
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
