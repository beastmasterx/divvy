// Settings command.

import '../../utils/i18n.dart';
import '../base/command.dart';

/// Settings command.
class SettingsCommand extends Command {
  @override
  String get description => translate('Settings');

  @override
  Future<void> execute(CommandContext context) async {
    // TODO: Handle settings
    print(translate('Settings not yet implemented.'));
  }
}
