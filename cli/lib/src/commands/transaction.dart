// Transaction management commands.

import '../models/session.dart';
import '../services/category.dart';
import '../services/period.dart';
import '../services/transaction.dart';
import '../ui/prompts.dart';
import '../ui/tables.dart';
import '../utils/i18n.dart';
import '../utils/validation.dart';
import 'package:divvy_api_client/divvy_api_client.dart';

/// Handle add transaction command.
Future<void> handleAddTransaction(
  TransactionService transactionService,
  PeriodService periodService,
  CategoryService categoryService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
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
    final categories = await categoryService.listCategories();
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

  final transaction = await transactionService.createTransaction(
    session.currentPeriodId!,
    request,
  );

  if (transaction != null) {
    print(translate('Transaction created successfully.'));
  } else {
    print(translate('Failed to create transaction.'));
  }
}

/// Handle view transactions command.
Future<void> handleViewTransactions(
  PeriodService periodService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
    print(translate('No period selected.'));
    return;
  }

  final transactions = await periodService.getTransactions(session.currentPeriodId!);
  if (transactions.isEmpty) {
    print(translate('No transactions available.'));
    return;
  }

  displayTable(
    headers: ['ID', 'Type', 'Amount', 'Description', 'Status'],
    rows: transactions.map((t) => [
      t.id.toString(),
      t.transactionKind.toString().split('.').last,
      formatAmount(t.amount),
      t.description ?? '',
      t.status.toString().split('.').last,
    ]).toList(),
  );
}

/// Handle approve transaction command.
Future<void> handleApproveTransaction(
  TransactionService transactionService,
  Session session,
) async {
  final transactionIdStr = promptString(translate('Transaction ID: '));
  if (transactionIdStr == null) {
    return;
  }

  final transactionId = int.tryParse(transactionIdStr);
  if (transactionId == null) {
    print(translate('Invalid transaction ID.'));
    return;
  }

  final transaction = await transactionService.approveTransaction(transactionId);
  if (transaction != null) {
    print(translate('Transaction approved successfully.'));
  } else {
    print(translate('Failed to approve transaction.'));
  }
}

/// Handle reject transaction command.
Future<void> handleRejectTransaction(
  TransactionService transactionService,
  Session session,
) async {
  final transactionIdStr = promptString(translate('Transaction ID: '));
  if (transactionIdStr == null) {
    return;
  }

  final transactionId = int.tryParse(transactionIdStr);
  if (transactionId == null) {
    print(translate('Invalid transaction ID.'));
    return;
  }

  final transaction = await transactionService.rejectTransaction(transactionId);
  if (transaction != null) {
    print(translate('Transaction rejected successfully.'));
  } else {
    print(translate('Failed to reject transaction.'));
  }
}

