// Config unset-context command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../option_parser.dart';

/// Config unset-context command - unsets group/period context.
class ConfigUnsetContextCommand extends Command with OptionParserMixin {
  @override
  String get description => translate('Unset Context');

  @override
  bool canExecute(Session session) => true;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      ensureTerminalState();

      // Parse --group and --period flags
      final hasGroupFlag = parseFlag(args, longName: 'group', shortName: 'g');
      final hasPeriodFlag = parseFlag(args, longName: 'period', shortName: 'p');

      bool hasChanges = false;

      // Unset group context (also clears period)
      if (hasGroupFlag) {
        if (context.session.currentGroupId != null) {
          context.session.currentGroupId = null;
          context.session.currentGroupName = null;
          context.session.currentPeriodId = null;
          context.session.currentPeriodName = null;
          context.config.preferences.setLastActiveGroup(null);
          context.config.preferences.setLastActivePeriod(null);
          hasChanges = true;
          print(translate('Group context unset.'));
        } else {
          print(translate('No group context set.'));
        }
      }

      // Unset period context
      if (hasPeriodFlag) {
        if (context.session.currentPeriodId != null) {
          context.session.currentPeriodId = null;
          context.session.currentPeriodName = null;
          context.config.preferences.setLastActivePeriod(null);
          hasChanges = true;
          print(translate('Period context unset.'));
        } else {
          print(translate('No period context set.'));
        }
      }

      if (!hasGroupFlag && !hasPeriodFlag) {
        print(translate('No context changes specified. Use --group or --period.'));
        return 1;
      }

      if (hasChanges) {
        // Save preferences
        await context.config.preferences.save();
      }
      return 0;
    } catch (e) {
      ensureTerminalState();
      print('Error: ${formatApiError(e)}');
      return 1;
    }
  }
}
