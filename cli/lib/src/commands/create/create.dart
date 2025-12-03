// Create command router - handles divvy create RESOURCE [args].

import '../base/command.dart';
import '../group/create.dart';
import '../period/create.dart';
import '../transaction/create.dart';

/// Create command router that delegates to resource-specific create commands.
class CreateCommand {
  final CommandContext context;

  CreateCommand(this.context);

  /// Execute create command.
  Future<int> execute(List<String> args) async {
    if (args.isEmpty) {
      _printUsage();
      return 1;
    }

    final resource = args[0].toLowerCase();
    final remainingArgs = args.sublist(1);

    final Command command;
    switch (resource) {
      case 'group':
      case 'groups':
        command = CreateGroupCommand();
        break;
      case 'period':
      case 'periods':
        command = CreatePeriodCommand();
        break;
      case 'transaction':
      case 'transactions':
        command = CreateTransactionCommand();
        break;
      default:
        print('Unknown resource type: $resource');
        _printUsage();
        return 1;
    }

    return await command.execute(context, args: remainingArgs);
  }

  void _printUsage() {
    print('Usage: divvy create RESOURCE [-f FILE | NAME] [flags]');
    print('');
    print('Resources:');
    print('  group, groups       Create a new group');
    print('  period, periods     Create a new period');
    print('  transaction, transactions  Create a new transaction');
    print('');
    print('Examples:');
    print('  divvy create group "My Group"');
    print('  divvy create group "My Group" --description="Description"');
    print('  divvy create period "January 2024"');
    print('  divvy create transaction -f transaction.yaml');
  }
}

