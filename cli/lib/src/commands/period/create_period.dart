// Create period command.

import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Create period command.
class CreatePeriodCommand extends Command {
  @override
  String get description => translate('Create Period');

  @override
  bool canExecute(Session session) => session.isAuthenticated && session.currentGroupId != null;

  @override
  Future<void> execute(CommandContext context) async {
    if (context.session.currentGroupId == null) {
      print(translate('No group selected.'));
      return;
    }

    final name = promptString(translate('Period Name: '));
    if (name == null || name.isEmpty) {
      print(translate('Period creation cancelled.'));
      return;
    }

    final period = await context.periodService.createPeriod(context.session.currentGroupId!, name);

    if (period != null) {
      print(translate('Period created successfully.'));
      context.session.setPeriod(period.id, period.name);

      // Save to preferences
      context.config.preferences.setLastActivePeriod(context.session.currentPeriodId!);
      await context.config.preferences.save();
    } else {
      print(translate('Failed to create period.'));
    }
  }
}
