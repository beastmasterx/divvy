// Delete command router - handles divvy delete RESOURCE ID or divvy delete -f FILE.

import '../base/command.dart';
import '../transaction/delete.dart';

/// Delete command router that delegates to resource-specific delete commands.
class DeleteCommand {
  final CommandContext context;

  DeleteCommand(this.context);

  /// Execute delete command.
  Future<int> execute(List<String> args) async {
    if (args.isEmpty) {
      _printUsage();
      return 1;
    }

    // Check if first arg is -f or --file (YAML file deletion)
    if (args[0] == '-f' || args[0] == '--file') {
      print('Delete from YAML file not yet implemented.');
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
        print('Delete group not yet implemented.');
        return 1;
      case 'period':
      case 'periods':
        print('Delete period not yet implemented.');
        return 1;
      case 'transaction':
      case 'transactions':
        command = DeleteTransactionCommand();
        break;
      default:
        print('Unknown resource type: $resource');
        _printUsage();
        return 1;
    }

    return await command.execute(context, args: remainingArgs);
  }

  void _printUsage() {
    print('Usage: divvy delete RESOURCE ID [flags]');
    print('       divvy delete -f FILE [flags]');
    print('');
    print('Resources:');
    print('  group, groups       Delete a group (not yet implemented)');
    print('  period, periods     Delete a period (not yet implemented)');
    print('  transaction, transactions  Delete a transaction (draft only)');
    print('');
    print('Examples:');
    print('  divvy delete transaction 123');
    print('  divvy delete -f resources.yaml');
  }
}

