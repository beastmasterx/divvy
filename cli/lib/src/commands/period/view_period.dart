// View period command.

import '../../api/schemas.dart';
import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../ui/tables.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// View period command.
class ViewPeriodCommand extends Command {
  @override
  String get description => translate('Select Period');

  @override
  bool canExecute(Session session) => session.isAuthenticated && session.currentGroupId != null;

  @override
  Future<void> execute(CommandContext context) async {
    // If period is already selected, show it
    if (context.session.currentPeriodId != null) {
      final period = await context.periodService.getPeriod(context.session.currentPeriodId!);
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
      return;
    }

    // If no period selected but group is selected, list periods and let user select
    if (context.session.currentGroupId != null) {
      final periods = await context.periodService.getPeriodsByGroup(context.session.currentGroupId!);
      if (periods.isEmpty) {
        print(translate('No periods available for this group.'));
        return;
      }

      displayList<PeriodResponse>(
        items: periods,
        itemToString: (p) => '${p.name} (${p.status})',
        header: translate('Select a period:'),
      );

      final choice = promptSelection('', periods.length);
      if (choice == null) {
        print(translate('Selection cancelled.'));
        return;
      }

      final selectedPeriod = periods[choice - 1];
      context.session.setPeriod(selectedPeriod.id, selectedPeriod.name);
      print(translate('Period selected: {}', [selectedPeriod.name]));

      // Save to preferences
      context.config.preferences.setLastActivePeriod(context.session.currentPeriodId!);
      await context.config.preferences.save();
      return;
    }

    // No group selected
    print(translate('No group selected.'));
  }
}
