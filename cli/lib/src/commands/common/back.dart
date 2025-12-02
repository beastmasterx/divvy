// Back command (goes back to previous menu).

import '../../utils/i18n.dart';
import '../base/command.dart';

/// Back command (goes back to previous menu level).
/// In submenus: exits submenu.
/// In main menus: clears current context to go back one level.
class BackCommand extends Command {
  @override
  String get description => translate('Back');

  @override
  Future<void> execute(CommandContext context) async {
    // In main menus: clear transaction context to go back to transaction list
    if (context.session.currentTransactionId != null) {
      context.session.currentTransactionId = null;
      context.session.currentTransactionDescription = null;
    } else if (context.session.currentPeriodId != null) {
      context.session.currentPeriodId = null;
      context.session.currentPeriodName = null;
    } else if (context.session.currentGroupId != null) {
      context.session.currentGroupId = null;
      context.session.currentGroupName = null;
    }
    // In submenus: menu loop will detect this command and exit submenu
  }
}
