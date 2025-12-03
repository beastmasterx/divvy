// Config set-context command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../option_parser.dart';

/// Config set-context command - sets group/period context.
class ConfigSetContextCommand extends Command with OptionParserMixin {
  @override
  String get description => translate('Set Context');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      if (!context.session.isAuthenticated) {
        print(translate('Authentication required.'));
        return 1;
      }

      ensureTerminalState();

      // Parse --group and --period flags
      String? groupIdentifier = parseOption(args, longName: 'group', shortName: 'g');
      String? periodIdentifier = parseOption(args, longName: 'period', shortName: 'p');

      bool hasChanges = false;

      // Set group context
      if (groupIdentifier != null) {
        int? groupId;

        // Try as ID first
        final id = int.tryParse(groupIdentifier);
        if (id != null) {
          final group = await context.groupService.getGroup(id);
          if (group == null) {
            print(translate('Group not found: {}', [groupIdentifier]));
            return 1;
          }
          groupId = group.id;
        } else {
          // Try as name
          final groups = await context.groupService.listGroups();
          final matchingGroups = groups.where((g) => g.name.toLowerCase() == groupIdentifier.toLowerCase()).toList();

          if (matchingGroups.isEmpty) {
            print(translate('Group not found: {}', [groupIdentifier]));
            return 1;
          }

          if (matchingGroups.length > 1) {
            print(translate('Multiple groups found with that name.'));
            return 1;
          }

          groupId = matchingGroups.first.id;
        }

        final group = await context.groupService.getGroup(groupId);
        if (group != null) {
          context.session.setGroup(groupId, group.name);
          context.config.preferences.setLastActiveGroup(groupId);
          hasChanges = true;
          print(translate('Group context set to: {} (ID: {})', [group.name, groupId]));
        }
      }

      // Set period context (requires group to be set)
      if (periodIdentifier != null) {
        if (context.session.currentGroupId == null) {
          print(translate('Group must be set before setting period context.'));
          return 1;
        }

        int? periodId;

        // Try as ID first
        final id = int.tryParse(periodIdentifier);
        if (id != null) {
          final period = await context.periodService.getPeriod(id);
          if (period == null) {
            print(translate('Period not found: {}', [periodIdentifier]));
            return 1;
          }
          // Verify period belongs to current group
          if (period.groupId != context.session.currentGroupId) {
            print(translate('Period does not belong to current group.'));
            return 1;
          }
          periodId = period.id;
        } else {
          // Try as name
          final periods = await context.periodService.getPeriodsByGroup(context.session.currentGroupId!);
          final matchingPeriods = periods.where((p) => p.name.toLowerCase() == periodIdentifier.toLowerCase()).toList();

          if (matchingPeriods.isEmpty) {
            print(translate('Period not found: {}', [periodIdentifier]));
            return 1;
          }

          if (matchingPeriods.length > 1) {
            print(translate('Multiple periods found with that name.'));
            return 1;
          }

          periodId = matchingPeriods.first.id;
        }

        final period = await context.periodService.getPeriod(periodId);
        if (period != null) {
          context.session.setPeriod(periodId, period.name);
          context.config.preferences.setLastActivePeriod(periodId);
          hasChanges = true;
          print(translate('Period context set to: {} (ID: {})', [period.name, periodId]));
        }
      }

      if (!hasChanges) {
        print(translate('No context changes specified. Use --group or --period.'));
        return 1;
      }

      // Save preferences
      await context.config.preferences.save();
      return 0;
    } catch (e) {
      ensureTerminalState();
      print('Error: ${formatApiError(e)}');
      return 1;
    }
  }
}
