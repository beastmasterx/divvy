// Get period command (list or get specific period).

import '../../api/schemas.dart';
import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/formatting.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../tables.dart';

/// Get period command - lists periods or gets a specific period.
class GetPeriodCommand extends Command {
  @override
  String get description => translate('Get Period');

  @override
  bool canExecute(Session session) => session.isAuthenticated && session.currentGroupId != null;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      if (context.session.currentGroupId == null) {
        print(translate('No group selected.'));
        return 1;
      }

      // If name/ID provided, get specific period
      if (args != null && args.isNotEmpty) {
        final identifier = args[0];

        // Try as ID first
        final id = int.tryParse(identifier);
        if (id != null) {
          final period = await context.periodService.getPeriod(id);
          if (period != null) {
            _printPeriod(period);
            return 0;
          } else {
            print(translate('Period not found.'));
            return 1;
          }
        }

        // Try as name
        final periods = await context.periodService.getPeriodsByGroup(context.session.currentGroupId!);
        final matchingPeriods = periods.where((p) => p.name.toLowerCase() == identifier.toLowerCase()).toList();

        if (matchingPeriods.isEmpty) {
          print(translate('Period not found.'));
          return 1;
        }

        if (matchingPeriods.length > 1) {
          print(translate('Multiple periods found with that name.'));
          return 1;
        }

        _printPeriod(matchingPeriods.first);
        return 0;
      }

      // No identifier - list all periods for current group
      final periods = await context.periodService.getPeriodsByGroup(context.session.currentGroupId!);
      if (periods.isEmpty) {
        print(translate('No periods available for this group.'));
        return 0;
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

      // Display periods in a table
      displayTable(
        headers: ['ID', 'Name', 'Status'],
        rows: periods.map((p) {
          final isCurrent = p.id == context.session.currentPeriodId;
          final marker = isCurrent ? ' (current)' : '';
          return [p.id.toString(), p.name, '${getEnumName(p.status)}$marker'];
        }).toList(),
      );

      return 0;
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }

  void _printPeriod(PeriodResponse period) {
    print('ID: ${period.id}');
    print('Name: ${period.name}');
    print('Status: ${getEnumName(period.status)}');
  }
}
