// Config command router.

import '../base/command.dart';
import 'current_context.dart';
import 'get.dart';
import 'set.dart';
import 'set_context.dart';
import 'unset_context.dart';
import 'view.dart';

/// Config command router that delegates to individual command classes.
class ConfigCommand {
  final CommandContext context;

  ConfigCommand(this.context);

  /// Execute config command.
  Future<int> execute(List<String> args) async {
    if (args.isEmpty) {
      _printUsage();
      return 1;
    }

    final subcommand = args[0];
    final remainingArgs = args.sublist(1);

    final Command command;
    switch (subcommand) {
      case 'view':
        command = ConfigViewCommand();
        break;
      case 'set-context':
        command = ConfigSetContextCommand();
        break;
      case 'unset-context':
        command = ConfigUnsetContextCommand();
        break;
      case 'current-context':
        command = ConfigCurrentContextCommand();
        break;
      case 'get':
        command = ConfigGetCommand();
        break;
      case 'set':
        command = ConfigSetCommand();
        break;
      default:
        print('Unknown config subcommand: $subcommand');
        _printUsage();
        return 1;
    }

    // Execute command with remaining args
    return await command.execute(context, args: remainingArgs);
  }

  void _printUsage() {
    print('Usage: divvy config <command> [options]');
    print('');
    print('Commands:');
    print('  view            View all configuration');
    print('  set-context     Set context (group, period)');
    print('  unset-context   Unset context (group, period)');
    print('  current-context Show current context');
    print('  get             Get a preference value');
    print('  set             Set a preference value');
    print('');
    print('Examples:');
    print('  divvy config view');
    print('  divvy config set-context --group="My Group"');
    print('  divvy config set-context --group=1 --period="January 2024"');
    print('  divvy config unset-context --group');
    print('  divvy config current-context');
    print('  divvy config get apiUrl');
    print('  divvy config set language en_US');
  }
}
