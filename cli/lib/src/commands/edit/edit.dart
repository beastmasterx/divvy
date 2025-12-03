// Edit command router - handles divvy edit RESOURCE ID.

import '../base/command.dart';
import '../transaction/edit.dart';

/// Edit command router that delegates to resource-specific edit commands.
class EditCommand {
  final CommandContext context;

  EditCommand(this.context);

  /// Execute edit command.
  Future<int> execute(List<String> args) async {
    if (args.isEmpty) {
      _printUsage();
      return 1;
    }

    final resource = args[0].toLowerCase();
    final remainingArgs = args.sublist(1);

    if (remainingArgs.isEmpty) {
      print('Error: Resource ID required');
      _printUsage();
      return 1;
    }

    final Command command;
    switch (resource) {
      case 'group':
      case 'groups':
        print('Edit group not yet implemented. Use YAML editor in future version.');
        return 1;
      case 'period':
      case 'periods':
        print('Edit period not yet implemented. Use YAML editor in future version.');
        return 1;
      case 'transaction':
      case 'transactions':
        command = EditTransactionCommand();
        break;
      default:
        print('Unknown resource type: $resource');
        _printUsage();
        return 1;
    }

    return await command.execute(context, args: remainingArgs);
  }

  void _printUsage() {
    print('Usage: divvy edit RESOURCE ID [flags]');
    print('');
    print('Resources:');
    print('  group, groups       Edit a group (not yet implemented)');
    print('  period, periods     Edit a period (not yet implemented)');
    print('  transaction, transactions  Edit a transaction (draft only)');
    print('');
    print('Examples:');
    print('  divvy edit transaction 123');
  }
}

