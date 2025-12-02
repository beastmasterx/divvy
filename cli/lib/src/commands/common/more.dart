// More menu command.

import '../../utils/i18n.dart';
import '../base/command.dart';

/// More menu command (triggers submenu).
class MoreCommand extends Command {
  @override
  String get description => translate('More...');

  @override
  Future<void> execute(CommandContext context) async {
    // This command is handled specially in the menu system
    // It triggers showing the "More" submenu
    // The actual submenu handling is done in App._handleMoreMenu
  }
}
