// Service layer for settlement operations.

import 'package:built_collection/built_collection.dart';
import '../api/divvy_client.dart';
import '../ui/displays.dart';
import '../utils/formatting.dart';

/// Get settlement plan.
///
/// Parameters:
/// - [client]: The API client
/// - [periodId]: Optional period ID (defaults to current period)
///
/// Returns:
/// List of settlement transactions
Future<List<TransactionDisplay>> getSettlementPlan(
  DivvyClient client, {
  int? periodId,
}) async {
  final response = await client.settlement
      .getSettlementPlanApiV1SettlementPlanGet(periodId: periodId);
  final plan = response.data;
  if (plan == null) {
    return [];
  }

  return plan.transactions.map((tx) {
    final amountFormatted = formatAmountWithSign(tx.amount);
    return TransactionDisplay(
      date: tx.date,
      category: '',
      type: tx.transactionType,
      split: '',
      amount: tx.amount,
      amountFormatted: amountFormatted,
      description: tx.description ?? '',
      payer: tx.fromTo,
    );
  }).toList();
}

/// Get settlement balances.
///
/// Parameters:
/// - [client]: The API client
///
/// Returns:
/// List of member balances with descriptions
Future<List<({String memberName, String balanceDescription})>>
getSettlementBalances(DivvyClient client) async {
  final response = await client.settlement
      .getSettlementBalancesApiV1SettlementBalancesGet();
  final balances = response.data?.balances ?? BuiltList();
  return balances
      .map(
        (b) => (
          memberName: b.memberName,
          balanceDescription: b.balanceDescription,
        ),
      )
      .toList();
}
