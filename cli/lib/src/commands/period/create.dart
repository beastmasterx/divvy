// Create period command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../option_parser.dart';
import '../prompts.dart';

/// Create period command.
class CreatePeriodCommand extends Command with OptionParserMixin {
  @override
  String get description => translate('Create Period');

  @override
  bool canExecute(Session session) => session.isAuthenticated && session.currentGroupId != null;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      if (context.session.currentGroupId == null) {
        print(translate('No group selected.'));
        return 1;
      }

      // Parse name from args or prompt
      final name = parseOption(
        args,
        longName: 'name',
        shortName: 'n',
        prompt: () => promptString(translate('Period Name: ')),
      );

      if (name == null || name.isEmpty) {
        print(translate('Period creation cancelled.'));
        return 1;
      }

      final period = await context.periodService.createPeriod(context.session.currentGroupId!, name);

      if (period != null) {
        print(translate('Period created successfully.'));
        context.session.setPeriod(period.id, period.name);

        // Save to preferences
        context.config.preferences.setLastActivePeriod(context.session.currentPeriodId!);
        await context.config.preferences.save();
        return 0;
      } else {
        print(translate('Failed to create period.'));
        return 1;
      }
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
