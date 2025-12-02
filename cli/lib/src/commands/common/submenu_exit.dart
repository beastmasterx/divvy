// Submenu exit command (exits submenu only).

import '../../utils/i18n.dart';
import '../base/command.dart';

/// Submenu exit command (exits submenu without exiting the application).
class SubmenuExitCommand extends Command {
  @override
  String get description => translate('Exit');

  @override
  Future<void> execute(CommandContext context) async {
    // This command does nothing - it's just used to exit the submenu
    // The menu loop will detect it and exit
  }
}
