/// Service layer for transaction operations.

import 'package:divvy_api_client/src/model/expense_create.dart';
import 'package:divvy_api_client/src/model/deposit_create.dart';
import 'package:divvy_api_client/src/model/refund_create.dart';
import '../api/divvy_client.dart';

/// Create an expense.
/// 
/// Parameters:
/// - [client]: The API client
/// - [description]: Expense description (optional)
/// - [amount]: Amount as dollar string (e.g., "123.45")
/// - [payerName]: Name of the member paying
/// - [categoryName]: Expense category name
/// - [isPersonal]: Whether this is a personal expense (not split)
/// - [expenseType]: Expense type: 'shared', 'personal', or 'individual' (default: 'individual')
/// 
/// Returns:
/// Success or error message
Future<String> createExpense(
  DivvyClient client,
  String amount,
  String payerName,
  String categoryName, {
  String? description,
  bool isPersonal = false,
  String? expenseType,
}) async {
  final request = ExpenseCreate((b) => b
    ..amount = amount
    ..payerName = payerName
    ..categoryName = categoryName
    ..description = description
    ..isPersonal = isPersonal
    ..expenseType = expenseType);
  final response = await client.transactions.createExpenseApiV1TransactionsExpensesPost(
    expenseCreate: request,
  );
  return response.data?.message ?? 'Success';
}

/// Create a deposit.
/// 
/// Parameters:
/// - [client]: The API client
/// - [description]: Deposit description (optional)
/// - [amount]: Amount as dollar string (e.g., "123.45")
/// - [payerName]: Name of the member making the deposit
/// 
/// Returns:
/// Success or error message
Future<String> createDeposit(
  DivvyClient client,
  String amount,
  String payerName, {
  String? description,
}) async {
  final request = DepositCreate((b) => b
    ..amount = amount
    ..payerName = payerName
    ..description = description);
  final response = await client.transactions.createDepositApiV1TransactionsDepositsPost(
    depositCreate: request,
  );
  return response.data?.message ?? 'Success';
}

/// Create a refund.
/// 
/// Parameters:
/// - [client]: The API client
/// - [description]: Refund description (optional)
/// - [amount]: Amount as dollar string (e.g., "123.45")
/// - [memberName]: Name of the member to refund
/// 
/// Returns:
/// Success or error message
Future<String> createRefund(
  DivvyClient client,
  String amount,
  String memberName, {
  String? description,
}) async {
  final request = RefundCreate((b) => b
    ..amount = amount
    ..memberName = memberName
    ..description = description);
  final response = await client.transactions.createRefundApiV1TransactionsRefundsPost(
    refundCreate: request,
  );
  return response.data?.message ?? 'Success';
}

