// Auth command implementation.

import '../base/command.dart';
import 'login.dart';
import 'logout.dart';
import 'register.dart';
import 'status.dart';

/// Auth command router that delegates to individual command classes.
class AuthCommand {
  final CommandContext context;

  AuthCommand(this.context);

  /// Execute auth command.
  Future<int> execute(List<String> args) async {
    if (args.isEmpty) {
      _printUsage();
      return 1;
    }

    final subcommand = args[0];
    final remainingArgs = args.sublist(1);

    final Command command;
    switch (subcommand) {
      case 'login':
        command = LoginCommand();
        break;
      case 'register':
        command = RegisterCommand();
        break;
      case 'logout':
        command = LogoutCommand();
        break;
      case 'status':
        command = StatusCommand();
        break;
      default:
        print('Unknown auth subcommand: $subcommand');
        _printUsage();
        return 1;
    }

    // Execute command with remaining args
    return await command.execute(context, args: remainingArgs);
  }

  void _printUsage() {
    print('Usage: divvy auth <command>');
    print('');
    print('Commands:');
    print('  login     Login with email and password');
    print('  register  Register a new user');
    print('  logout    Logout and clear tokens');
    print('  status    Show authentication status');
    print('');
    print('Examples:');
    print('  divvy auth login');
    print('  divvy auth login -u user@example.com');
    print('  divvy auth login -u user@example.com -p');
    print('  divvy auth register -u user@example.com --name="John Doe"');
  }
}
