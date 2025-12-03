// Period command router.

import '../base/command.dart';
import 'balances.dart';
import 'close.dart';
import 'settlement.dart';

/// Period command router that delegates to individual command classes.
class PeriodCommand {
  final CommandContext context;

  PeriodCommand(this.context);

  /// Execute period command.
  Future<int> execute(List<String> args) async {
    if (args.isEmpty) {
      _printUsage();
      return 1;
    }

    final subcommand = args[0];
    final remainingArgs = args.sublist(1);

    final Command command;
    switch (subcommand) {
      case 'close':
        command = ClosePeriodCommand();
        break;
      case 'balances':
      case 'balance':
        command = GetBalancesCommand();
        break;
      case 'settlement':
      case 'plan':
      case 'apply':
        command = SettlementCommand();
        break;
      default:
        print('Unknown period subcommand: $subcommand');
        _printUsage();
        return 1;
    }

    // Execute command with remaining args
    return await command.execute(context, args: remainingArgs);
  }

  void _printUsage() {
    print('Usage: divvy period <command> [options]');
    print('');
    print('Commands:');
    print('  close        Close a period');
    print('  balances     Show balances for a period');
    print('  settlement   Show settlement plan (optionally apply with --apply)');
    print('');
    print('Examples:');
    print('  divvy period close "January 2024"');
    print('  divvy period balances');
    print('  divvy period settlement --apply');
    print('');
    print('Note: Use "divvy get period" to list periods, "divvy create period" to create.');
  }
}
