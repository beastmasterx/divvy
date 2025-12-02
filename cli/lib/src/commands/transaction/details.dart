// View transaction details command.

import '../../models/session.dart';
import '../../ui/tables.dart';
import '../../utils/formatting.dart';
import '../../utils/i18n.dart';
import '../base/command.dart';

/// View transaction details command.
class ViewTransactionDetailsCommand extends Command {
  @override
  String get description => translate('View Details');

  @override
  bool canExecute(Session session) =>
      session.isAuthenticated &&
      session.currentGroupId != null &&
      session.currentPeriodId != null &&
      session.currentTransactionId != null;

  @override
  Future<void> execute(CommandContext context) async {
    if (context.session.currentTransactionId == null) {
      print(translate('No transaction selected.'));
      return;
    }

    final transaction = await context.transactionService.getTransaction(context.session.currentTransactionId!);
    if (transaction == null) {
      print(translate('Transaction not found.'));
      return;
    }

    print('\n${translate('Transaction Details')}:');
    print('${translate('ID')}: ${transaction.id}');
    print('${translate('Type')}: ${getEnumName(transaction.transactionKind)}');
    print('${translate('Amount')}: ${formatAmount(transaction.amount)}');
    print('${translate('Description')}: ${transaction.description ?? translate('No description')}');
    print('${translate('Payer')}: ${transaction.payerName ?? transaction.payerId}');
    print('${translate('Status')}: ${getEnumName(transaction.status)}');
    if (transaction.categoryName != null) {
      print('${translate('Category')}: ${transaction.categoryName}');
    }
  }
}
