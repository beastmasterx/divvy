// Add transaction command.

import '../../api/schemas.dart';
import '../../models/session.dart';
import '../../ui/prompts.dart';
import '../../ui/tables.dart';
import '../../utils/i18n.dart';
import '../../utils/validation.dart';
import '../base/command.dart';

/// Add transaction command.
class AddTransactionCommand extends Command {
  @override
  String get description => translate('Add Transaction');

  @override
  bool canExecute(Session session) =>
      session.isAuthenticated && session.currentGroupId != null && session.currentPeriodId != null;

  @override
  Future<void> execute(CommandContext context) async {
    if (context.session.currentPeriodId == null) {
      print(translate('No period selected.'));
      return;
    }

    // Get transaction kind
    print('\nTransaction Type:');
    print('1. Expense');
    print('2. Deposit');
    print('3. Refund');
    final typeChoice = promptSelection('Select type (1-3): ', 3);
    if (typeChoice == null) {
      print(translate('Transaction creation cancelled.'));
      return;
    }

    TransactionKind kind;
    switch (typeChoice) {
      case 1:
        kind = TransactionKind.expense;
        break;
      case 2:
        kind = TransactionKind.deposit;
        break;
      case 3:
        kind = TransactionKind.refund;
        break;
      default:
        print(translate('Invalid choice.'));
        return;
    }

    // Get description
    final description = promptString(translate('Description (optional): '), required: false);

    // Get amount
    final amountStr = promptString(translate('Amount: '));
    if (amountStr == null) {
      print(translate('Transaction creation cancelled.'));
      return;
    }

    final amountValidation = validateAmount(amountStr);
    if (!amountValidation.isValid) {
      print(amountValidation.errorMessage);
      return;
    }

    // Get category (for expenses)
    int? categoryId;
    if (kind == TransactionKind.expense) {
      final categories = await context.categoryService.listCategories();
      if (categories.isEmpty) {
        print(translate('No categories available.'));
        return;
      }

      displayList<CategoryResponse>(
        items: categories,
        itemToString: (c) => c.name,
        header: translate('Select category:'),
      );

      final catChoice = promptSelection('', categories.length);
      if (catChoice == null) {
        print(translate('Transaction creation cancelled.'));
        return;
      }
      categoryId = categories[catChoice - 1].id;
    }

    // Get payer (for expenses and deposits)
    int? payerId;
    if (kind == TransactionKind.expense || kind == TransactionKind.deposit) {
      // For now, we'll need to get current user or prompt
      // This is simplified - in real implementation, get from session or user service
      payerId = 1; // Placeholder
    }

    // Create transaction request
    final request = TransactionRequest((b) {
      b.amount = amountValidation.amountInCents;
      b.transactionKind = kind;
      b.splitKind = SplitKind.equal; // Default to equal split
      if (description != null && description.isNotEmpty) {
        b.description = description;
      }
      if (categoryId != null) {
        b.categoryId = categoryId;
      }
      if (payerId != null) {
        b.payerId = payerId;
      }
    });

    final transaction = await context.transactionService.createTransaction(context.session.currentPeriodId!, request);

    if (transaction != null) {
      print(translate('Transaction created successfully.'));
    } else {
      print(translate('Failed to create transaction.'));
    }
  }
}
