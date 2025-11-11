/// Service layer for period operations.

import 'package:divvy_api_client/src/model/period_response.dart';
import 'package:divvy_api_client/src/model/period_settle_request.dart';
import 'package:built_collection/built_collection.dart';
import '../api/divvy_client.dart';
import '../services/members.dart';
import '../ui/displays.dart';
import '../utils/formatting.dart';

/// Period data structure
class Period {
  final int id;
  final String name;
  final DateTime startDate;
  final DateTime? endDate;
  final bool isSettled;
  final DateTime? settledDate;

  Period({
    required this.id,
    required this.name,
    required this.startDate,
    this.endDate,
    required this.isSettled,
    this.settledDate,
  });
}

/// List all periods.
/// 
/// Parameters:
/// - [client]: The API client
/// 
/// Returns:
/// List of periods, ordered by start_date descending
Future<List<Period>> listPeriods(DivvyClient client) async {
  final response = await client.periods.listPeriodsApiV1PeriodsGet();
  final periods = response.data ?? BuiltList<PeriodResponse>();
  return periods.map((p) => Period(
    id: p.id,
    name: p.name,
    startDate: p.startDate,
    endDate: p.endDate,
    isSettled: p.isSettled,
    settledDate: p.settledDate,
  )).toList();
}

/// Get current active period.
/// 
/// Parameters:
/// - [client]: The API client
/// 
/// Returns:
/// Current period, or null if not found
Future<Period?> getCurrentPeriod(DivvyClient client) async {
  try {
    final response = await client.periods.getCurrentPeriodApiV1PeriodsCurrentGet();
    final p = response.data;
    if (p == null) return null;
    return Period(
      id: p.id,
      name: p.name,
      startDate: p.startDate,
      endDate: p.endDate,
      isSettled: p.isSettled,
      settledDate: p.settledDate,
    );
  } catch (e) {
    return null;
  }
}

/// Parse balance description to extract balance in cents.
/// 
/// Examples: "Is owed $123.45" -> 12345, "Owes $67.89" -> -6789, "Settled" -> 0
int _parseBalanceDescription(String description) {
  if (description.toLowerCase().contains('settled')) {
    return 0;
  }
  // Try to extract dollar amount from description
  final regex = RegExp(r'\$?([\d,]+\.?\d*)');
  final match = regex.firstMatch(description);
  if (match != null) {
    final amountStr = match.group(1)?.replaceAll(',', '') ?? '0';
    final amount = double.tryParse(amountStr) ?? 0.0;
    final cents = (amount * 100).round();
    if (description.toLowerCase().contains('owes')) {
      return -cents;
    } else {
      return cents;
    }
  }
  return 0;
}

/// Get period summary.
/// 
/// Parameters:
/// - [client]: The API client
/// - [periodId]: Period ID (null for current period)
/// 
/// Returns:
/// Period summary data
Future<PeriodSummaryData> getPeriodSummary(
  DivvyClient client, {
  int? periodId,
}) async {
  final response = periodId == null
      ? await client.periods.getCurrentPeriodSummaryApiV1PeriodsCurrentSummaryGet()
      : await client.periods.getPeriodSummaryApiV1PeriodsPeriodIdSummaryGet(
          periodId: periodId,
        );
  
  final summary = response.data;
  if (summary == null) {
    throw Exception('Period summary not found');
  }
  
  // Get active members to get paidRemainder info
  final activeMembers = await listMembers(client, activeOnly: true);
  final memberMap = {for (var m in activeMembers) m.name: m};
  
  // Convert transactions
  final transactions = summary.transactions.map((tx) {
    final dateOnly = tx.timestamp.toLocal().toString().split(' ')[0];
    final category = tx.categoryName ?? '';
    final type = tx.transactionType;
    final amount = tx.amount;
    final amountFormatted = formatAmountWithSign(amount);
    final description = tx.description ?? '';
    final payer = tx.payerName ?? '';
    
    // Determine split type
    String split;
    if (type == 'expense') {
      if (tx.isPersonal) {
        split = 'Personal';
      } else {
        // Check if payer is virtual (shared fund)
        split = 'Individual';
      }
    } else {
      split = '';
    }
    
    return TransactionDisplay(
      date: dateOnly,
      category: category,
      type: type,
      split: split,
      amount: amount,
      amountFormatted: amountFormatted,
      description: description,
      payer: payer,
    );
  }).toList();
  
  // Convert member balances
  final memberBalances = summary.balances.map((balance) {
    final member = memberMap[balance.memberName];
    final balanceCents = _parseBalanceDescription(balance.balanceDescription);
    return (
      name: balance.memberName,
      balance: balanceCents,
      paidRemainder: member?.paidRemainderInCycle ?? false,
    );
  }).toList();
  
  // Calculate public fund balance from transactions
  int publicFundBalance = 0;
  for (final tx in summary.transactions) {
    if (tx.transactionType == 'deposit' && tx.amount > 0) {
      // Check if payer is virtual member (public fund)
      if (tx.payerName?.toLowerCase().contains('public fund') ?? false) {
        publicFundBalance += tx.amount;
      }
    } else if (tx.transactionType == 'expense') {
      // Check if payer is virtual member
      if (tx.payerName?.toLowerCase().contains('public fund') ?? false) {
        publicFundBalance -= tx.amount;
      }
    }
  }
  
  return PeriodSummaryData(
    periodId: summary.period.id,
    periodName: summary.period.name,
    startDate: summary.period.startDate,
    endDate: summary.period.endDate,
    isSettled: summary.period.isSettled,
    settledDate: summary.period.settledDate,
    transactions: transactions,
    deposits: summary.totals.deposits,
    depositsFormatted: summary.totals.depositsFormatted,
    expenses: summary.totals.expenses,
    expensesFormatted: summary.totals.expensesFormatted,
    publicFundBalance: publicFundBalance,
    memberBalances: memberBalances,
  );
}

/// Settle current period.
/// 
/// Parameters:
/// - [client]: The API client
/// - [periodName]: Optional name for new period
/// 
/// Returns:
/// Success or error message
Future<String> settleCurrentPeriod(
  DivvyClient client, {
  String? periodName,
}) async {
  final request = PeriodSettleRequest((b) {
    if (periodName != null) {
      b.periodName = periodName;
    }
  });
  final response = await client.periods.settleCurrentPeriodApiV1PeriodsCurrentSettlePost(
    periodSettleRequest: request,
  );
  return response.data?.message ?? 'Success';
}

