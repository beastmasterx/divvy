// Get command router - handles divvy get RESOURCE [ID].

import '../base/command.dart';
import '../group/get.dart';
import '../period/get.dart';
import '../transaction/get.dart';

/// Get command router that delegates to resource-specific get commands.
class GetCommand {
  final CommandContext context;

  GetCommand(this.context);

  /// Execute get command.
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
        command = GetGroupCommand();
        break;
      case 'period':
      case 'periods':
        command = GetPeriodCommand();
        break;
      case 'transaction':
      case 'transactions':
        command = GetTransactionCommand();
        break;
      default:
        print('Unknown resource type: $resource');
        _printUsage();
        return 1;
    }

    return await command.execute(context, args: remainingArgs);
  }

  void _printUsage() {
    print('Usage: divvy get RESOURCE [ID] [flags]');
    print('');
    print('Resources:');
    print('  group, groups       List groups or get a specific group');
    print('  period, periods     List periods or get a specific period');
    print('  transaction, transactions  List transactions or get a specific transaction');
    print('');
    print('Examples:');
    print('  divvy get group');
    print('  divvy get group "My Group"');
    print('  divvy get period');
    print('  divvy get transaction 123');
  }
}

