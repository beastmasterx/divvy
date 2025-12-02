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

/// Handle select transaction command.
Future<void> handleSelectTransaction(
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

  displayList<TransactionResponse>(
    items: transactions,
    itemToString: (t) => 'ID ${t.id}: ${formatAmount(t.amount)} - ${t.description ?? translate('No description')} (${t.status.toString().split('.').last})',
    header: translate('Select a transaction:'),
  );

  final choice = promptSelection('', transactions.length);
  if (choice == null) {
    print(translate('Selection cancelled.'));
    return;
  }

  final selectedTransaction = transactions[choice - 1];
  session.setTransaction(selectedTransaction.id, selectedTransaction.description);
  print(translate('Transaction selected: ID {}', [selectedTransaction.id]));
}

/// Handle view transaction details command.
Future<void> handleViewTransactionDetails(
  TransactionService transactionService,
  Session session,
) async {
  if (session.currentTransactionId == null) {
    print(translate('No transaction selected.'));
    return;
  }

  final transaction = await transactionService.getTransaction(session.currentTransactionId!);
  if (transaction == null) {
    print(translate('Transaction not found.'));
    return;
  }

  print('\n${translate('Transaction Details')}:');
  print('${translate('ID')}: ${transaction.id}');
  print('${translate('Type')}: ${transaction.transactionKind.toString().split('.').last}');
  print('${translate('Amount')}: ${formatAmount(transaction.amount)}');
  print('${translate('Description')}: ${transaction.description ?? translate('No description')}');
  print('${translate('Payer')}: ${transaction.payerName ?? transaction.payerId}');
  print('${translate('Status')}: ${transaction.status.toString().split('.').last}');
  if (transaction.categoryName != null) {
    print('${translate('Category')}: ${transaction.categoryName}');
  }
}

/// Handle approve/reject transactions flow.
Future<void> handleApproveTransactionsFlow(
  PeriodService periodService,
  TransactionService transactionService,
  Session session,
) async {
  if (session.currentPeriodId == null) {
    print(translate('No period selected.'));
    return;
  }

  // Get all transactions and filter for pending ones
  final allTransactions = await periodService.getTransactions(session.currentPeriodId!);
  final pendingTransactions = allTransactions
      .where((t) => t.status.toString().split('.').last == 'pending')
      .toList();

  if (pendingTransactions.isEmpty) {
    print(translate('No pending transactions to approve.'));
    return;
  }

  print('\n${translate('Pending Transactions')}:');
  displayList<TransactionResponse>(
    items: pendingTransactions,
    itemToString: (t) => 'ID ${t.id}: ${formatAmount(t.amount)} - ${t.description ?? translate('No description')}',
    header: translate('Select a transaction to approve/reject:'),
  );

  final choice = promptSelection('', pendingTransactions.length);
  if (choice == null) {
    print(translate('Selection cancelled.'));
    return;
  }

  final selectedTransaction = pendingTransactions[choice - 1];

  // Show transaction details
  print('\n${translate('Transaction Details')}:');
  print('${translate('ID')}: ${selectedTransaction.id}');
  print('${translate('Type')}: ${selectedTransaction.transactionKind.toString().split('.').last}');
  print('${translate('Amount')}: ${formatAmount(selectedTransaction.amount)}');
  print('${translate('Description')}: ${selectedTransaction.description ?? translate('No description')}');
  print('${translate('Payer')}: ${selectedTransaction.payerName ?? selectedTransaction.payerId}');
  print('${translate('Status')}: ${selectedTransaction.status.toString().split('.').last}');

  // Ask for action
  print('\n${translate('Action')}:');
  print('1. ${translate('Approve')}');
  print('2. ${translate('Reject')}');
  print('3. ${translate('Cancel')}');

  final actionChoice = promptSelection(translate('Select action (1-3): '), 3);
  if (actionChoice == null || actionChoice == 3) {
    print(translate('Action cancelled.'));
    return;
  }

  if (actionChoice == 1) {
    // Approve
    final transaction = await transactionService.approveTransaction(selectedTransaction.id);
    if (transaction != null) {
      print(translate('Transaction approved successfully.'));
    } else {
      print(translate('Failed to approve transaction.'));
    }
  } else if (actionChoice == 2) {
    // Reject
    final transaction = await transactionService.rejectTransaction(selectedTransaction.id);
    if (transaction != null) {
      print(translate('Transaction rejected successfully.'));
    } else {
      print(translate('Failed to reject transaction.'));
    }
  }
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
  if (session.currentTransactionId == null) {
    print(translate('No transaction selected.'));
    return;
  }

  final transaction = await transactionService.rejectTransaction(session.currentTransactionId!);
  if (transaction != null) {
    print(translate('Transaction rejected successfully.'));
  } else {
    print(translate('Failed to reject transaction.'));
  }
}

/// Handle edit transaction command (draft only).
Future<void> handleEditTransaction(
  TransactionService transactionService,
  PeriodService periodService,
  CategoryService categoryService,
  Session session,
) async {
  if (session.currentTransactionId == null) {
    print(translate('No transaction selected.'));
    return;
  }

  final transaction = await transactionService.getTransaction(session.currentTransactionId!);
  if (transaction == null) {
    print(translate('Transaction not found.'));
    return;
  }

  // Check if transaction is in draft status
  if (transaction.status.toString().split('.').last != 'draft') {
    print(translate('Only draft transactions can be edited.'));
    return;
  }

  // TODO: Implement full edit flow as guided flow
  // For now, just show a message
  print(translate('Transaction editing flow not yet implemented.'));
  print(translate('Current transaction: ID {}', [transaction.id]));
}

/// Handle delete transaction command (draft only).
Future<void> handleDeleteTransaction(
  TransactionService transactionService,
  Session session,
) async {
  if (session.currentTransactionId == null) {
    print(translate('No transaction selected.'));
    return;
  }

  final transaction = await transactionService.getTransaction(session.currentTransactionId!);
  if (transaction == null) {
    print(translate('Transaction not found.'));
    return;
  }

  // Check if transaction is in draft status
  if (transaction.status.toString().split('.').last != 'draft') {
    print(translate('Only draft transactions can be deleted.'));
    return;
  }

  final confirm = promptYesNo(translate('Delete this transaction?'), defaultYes: false);
  if (!confirm) {
    print(translate('Deletion cancelled.'));
    return;
  }

  final success = await transactionService.deleteTransaction(session.currentTransactionId!);
  if (success) {
    print(translate('Transaction deleted successfully.'));
    session.currentTransactionId = null;
    session.currentTransactionDescription = null;
  } else {
    print(translate('Failed to delete transaction.'));
  }
}

/// Handle submit transaction command (draft only).
Future<void> handleSubmitTransaction(
  TransactionService transactionService,
  Session session,
) async {
  if (session.currentTransactionId == null) {
    print(translate('No transaction selected.'));
    return;
  }

  final transaction = await transactionService.getTransaction(session.currentTransactionId!);
  if (transaction == null) {
    print(translate('Transaction not found.'));
    return;
  }

  // Check if transaction is in draft status
  if (transaction.status.toString().split('.').last != 'draft') {
    print(translate('Only draft transactions can be submitted.'));
    return;
  }

  final confirm = promptYesNo(translate('Submit this transaction for approval?'), defaultYes: false);
  if (!confirm) {
    print(translate('Submission cancelled.'));
    return;
  }

  final updatedTransaction = await transactionService.submitTransaction(session.currentTransactionId!);
  if (updatedTransaction != null) {
    print(translate('Transaction submitted successfully.'));
  } else {
    print(translate('Failed to submit transaction.'));
  }
}

