// Select period command.

import '../../api/schemas.dart';
import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../ui/tables.dart';
import '../../utils/formatting.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// Select period command.
class SelectPeriodCommand extends Command {
  @override
  String get description => translate('Select Period');

  @override
  bool canExecute(Session session) => session.isAuthenticated && session.currentGroupId != null;

  @override
  Future<void> execute(CommandContext context) async {
    if (context.session.currentGroupId == null) {
      print(translate('No group selected.'));
      return;
    }

    final periods = await context.periodService.getPeriodsByGroup(context.session.currentGroupId!);
    if (periods.isEmpty) {
      print(translate('No periods available for this group.'));
      return;
    }

    // Show current selection if any
    if (context.session.currentPeriodId != null) {
      final currentPeriod = await context.periodService.getPeriod(context.session.currentPeriodId!);
      if (currentPeriod != null) {
        print('\n${translate('Current Period')}: ${currentPeriod.name}');
        print('${translate('Status')}: ${getEnumName(currentPeriod.status)}');
        print('');
      }
    }

    // Always show list to allow selection/change
    displayList<PeriodResponse>(
      items: periods,
      itemToString: (p) {
        final isCurrent = p.id == context.session.currentPeriodId;
        final marker = isCurrent ? ' (${translate('current')})' : '';
        return '${p.name} (${getEnumName(p.status)})$marker';
      },
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
  }
}
