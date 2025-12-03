// Get transactions command - lists transactions for a period or gets a specific transaction.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/formatting.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';
import '../tables.dart';

/// Get transactions command - lists transactions for a period or gets a specific transaction.
class GetTransactionCommand extends Command {
  @override
  String get description => translate('Get Transaction');

  @override
  bool canExecute(Session session) => session.isAuthenticated;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      // If no args, or first arg is a transaction ID, get specific transaction
      if (args != null && args.isNotEmpty) {
        final identifier = args[0];
        final transactionId = int.tryParse(identifier);

        if (transactionId != null) {
          // It's a transaction ID - get specific transaction
          final transaction = await context.transactionService.getTransaction(transactionId);
          if (transaction == null) {
            print(translate('Transaction not found.'));
            return 1;
          }

          print('\n${translate('Transaction Details')}:');
          print('${translate('ID')}: ${transaction.id}');
          print('${translate('Type')}: ${getEnumName(transaction.transactionKind)}');
          print('${translate('Amount')}: ${formatAmount(transaction.amount)}');
          print('${translate('Description')}: ${transaction.description ?? translate('No description')}');
          print('${translate('Payer')}: ${transaction.payerName ?? transaction.payerId.toString()}');
          print('${translate('Status')}: ${getEnumName(transaction.status)}');
          if (transaction.categoryName != null) {
            print('${translate('Category')}: ${transaction.categoryName}');
          }

          return 0;
        }
      }

      // Otherwise, list transactions for a period
      if (context.session.currentPeriodId == null) {
        print(translate('No period selected.'));
        return 1;
      }

      // Use period from args if provided, otherwise use current period
      int? periodId = context.session.currentPeriodId;

      if (args != null && args.isNotEmpty) {
        final identifier = args[0];
        final id = int.tryParse(identifier);
        if (id != null) {
          periodId = id;
        } else {
          // Try to find by name
          if (context.session.currentGroupId == null) {
            print(translate('No group selected.'));
            return 1;
          }
          final periods = await context.periodService.getPeriodsByGroup(context.session.currentGroupId!);
          final matching = periods.where((p) => p.name.toLowerCase() == identifier.toLowerCase()).toList();
          if (matching.isEmpty) {
            print(translate('Period not found.'));
            return 1;
          }
          if (matching.length > 1) {
            print(translate('Multiple periods found with that name.'));
            return 1;
          }
          periodId = matching.first.id;
        }
      }

      if (periodId == null) {
        print(translate('No period specified or selected.'));
        return 1;
      }

      final transactions = await context.periodService.getTransactions(periodId);
      if (transactions.isEmpty) {
        print(translate('No transactions available.'));
        return 0;
      }

      displayTable(
        headers: ['ID', 'Type', 'Description', 'Amount', 'Status'],
        rows: transactions
            .map(
              (t) => [
                t.id.toString(),
                getEnumName(t.transactionKind),
                t.description ?? '',
                formatAmount(t.amount),
                getEnumName(t.status),
              ],
            )
            .toList(),
      );

      return 0;
    } catch (e) {
      ensureTerminalState();
      print(formatApiError(e));
      return 1;
    }
  }
}
