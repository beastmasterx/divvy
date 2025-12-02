// Back to transactions command.

import '../../utils/i18n.dart';
import '../base/command.dart';

/// Back to transactions command (clears transaction context).
class BackToTransactionsCommand extends Command {
  @override
  String get description => translate('Back to Transactions');

  @override
  Future<void> execute(CommandContext context) async {
    // Back to Transactions
    context.session.currentTransactionId = null;
    context.session.currentTransactionDescription = null;
  }
}
