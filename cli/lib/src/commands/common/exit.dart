// Exit command.

import 'dart:io';

import '../../utils/i18n.dart';
import '../base/command.dart';

/// Exit command.
class ExitCommand extends Command {
  @override
  String get description => translate('Exit');

  @override
  Future<void> execute(CommandContext context) async {
    print(translate('Exiting Divvy. Goodbye!'));
    exit(0);
  }
}
