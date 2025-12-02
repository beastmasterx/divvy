// Back to top command.

import '../../utils/i18n.dart';
import '../base/command.dart';

/// Back to top command (clears all context).
class BackToTopCommand extends Command {
  @override
  String get description => translate('Back to Top');

  @override
  Future<void> execute(CommandContext context) async {
    // Back to Top - clear all context
    context.session.currentGroupId = null;
    context.session.currentGroupName = null;
    context.session.currentPeriodId = null;
    context.session.currentPeriodName = null;
    context.session.currentTransactionId = null;
    context.session.currentTransactionDescription = null;
  }
}
