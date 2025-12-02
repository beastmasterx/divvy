// Service layer for period operations.

import 'package:divvy_api_client/divvy_api_client.dart';

import '../api/client.dart';

/// Period service for managing periods.
class PeriodService {
  final DivvyClient _client;

  PeriodService(this._client);

  /// Get a period by ID.
  Future<PeriodResponse?> getPeriod(int periodId) async {
    try {
      final response = await _client.periods.getPeriodApiV1PeriodsPeriodIdGet(
        periodId: periodId,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Update a period.
  Future<PeriodResponse?> updatePeriod(int periodId, String name) async {
    try {
      final request = PeriodRequest((b) => b..name = name);
      final response = await _client.periods.updatePeriodApiV1PeriodsPeriodIdPut(
        periodId: periodId,
        periodRequest: request,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Close a period.
  Future<PeriodResponse?> closePeriod(int periodId) async {
    try {
      final response =
          await _client.periods.closePeriodApiV1PeriodsPeriodIdClosePut(
        periodId: periodId,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Get transactions for a period.
  Future<List<TransactionResponse>> getTransactions(int periodId) async {
    try {
      final response =
          await _client.periods.getTransactionsApiV1PeriodsPeriodIdTransactionsGet(
        periodId: periodId,
      );
      return response.data?.toList() ?? [];
    } catch (e) {
      return [];
    }
  }

  /// Get balances for a period.
  Future<List<BalanceResponse>> getBalances(int periodId) async {
    try {
      final response =
          await _client.periods.getBalancesApiV1PeriodsPeriodIdBalancesGet(
        periodId: periodId,
      );
      return response.data?.toList() ?? [];
    } catch (e) {
      return [];
    }
  }

  /// Get settlement plan for a period.
  Future<List<SettlementResponse>> getSettlementPlan(int periodId) async {
    try {
      final response = await _client.periods
          .getSettlementPlanApiV1PeriodsPeriodIdGetSettlementPlanGet(
        periodId: periodId,
      );
      return response.data?.toList() ?? [];
    } catch (e) {
      return [];
    }
  }

  /// Apply settlement plan for a period.
  Future<bool> applySettlementPlan(int periodId) async {
    try {
      await _client.periods
          .applySettlementPlanApiV1PeriodsPeriodIdApplySettlementPlanPost(
        periodId: periodId,
      );
      return true;
    } catch (e) {
      return false;
    }
  }

  /// Get periods for a group.
  Future<List<PeriodResponse>> getPeriodsByGroup(int groupId) async {
    try {
      final response = await _client.groups.getPeriodsApiV1GroupsGroupIdPeriodsGet(
        groupId: groupId,
      );
      return response.data?.toList() ?? [];
    } catch (e) {
      return [];
    }
  }
}

