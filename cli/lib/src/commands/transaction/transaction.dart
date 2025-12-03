// Transaction command router.

import '../base/command.dart';
import 'approve.dart';
import 'reject.dart';
import 'submit.dart';

/// Transaction command router that delegates to individual command classes.
class TransactionCommand {
  final CommandContext context;

  TransactionCommand(this.context);

  /// Execute transaction command.
  Future<int> execute(List<String> args) async {
    if (args.isEmpty) {
      _printUsage();
      return 1;
    }

    final subcommand = args[0];
    final remainingArgs = args.sublist(1);

    final Command command;
    switch (subcommand) {
      case 'approve':
        command = ApproveTransactionCommand();
        break;
      case 'reject':
        command = RejectTransactionCommand();
        break;
      case 'submit':
        command = SubmitTransactionCommand();
        break;
      default:
        print('Unknown transaction subcommand: $subcommand');
        _printUsage();
        return 1;
    }

    // Execute command with remaining args
    return await command.execute(context, args: remainingArgs);
  }

  void _printUsage() {
    print('Usage: divvy transaction <command> [options]');
    print('');
    print('Commands:');
    print('  approve   Approve a transaction (by ID)');
    print('  reject    Reject a transaction (by ID)');
    print('  submit    Submit a draft transaction (by ID)');
    print('');
    print('Examples:');
    print('  divvy transaction approve 123');
    print('  divvy transaction reject 123');
    print('  divvy transaction submit 123');
    print('');
    print('Note: Use "divvy get transaction" to list transactions, "divvy create transaction" to create.');
  }
}
