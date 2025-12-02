// Service layer for transaction operations.

import '../api/client.dart';
import '../api/schemas.dart';

/// Transaction service for managing transactions.
class TransactionService {
  final DivvyClient _client;

  TransactionService(this._client);

  /// Get a transaction by ID.
  Future<TransactionResponse?> getTransaction(int transactionId) async {
    try {
      final response = await _client.transactions
          .getTransactionByIdApiV1TransactionsTransactionIdGet(
        transactionId: transactionId,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Create a transaction in a period.
  Future<TransactionResponse?> createTransaction(
    int periodId,
    TransactionRequest request,
  ) async {
    try {
      final response = await _client.periods
          .createTransactionApiV1PeriodsPeriodIdTransactionsPost(
        periodId: periodId,
        transactionRequest: request,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Update a transaction.
  Future<TransactionResponse?> updateTransaction(
    int transactionId,
    TransactionRequest request,
  ) async {
    try {
      final response = await _client.transactions
          .updateTransactionApiV1TransactionsTransactionIdPut(
        transactionId: transactionId,
        transactionRequest: request,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Delete a transaction.
  Future<bool> deleteTransaction(int transactionId) async {
    try {
      await _client.transactions
          .deleteTransactionApiV1TransactionsTransactionIdDelete(
        transactionId: transactionId,
      );
      return true;
    } catch (e) {
      return false;
    }
  }

  /// Submit a transaction (draft -> pending).
  Future<TransactionResponse?> submitTransaction(int transactionId) async {
    try {
      final response = await _client.transactions
          .submitTransactionApiV1TransactionsTransactionIdSubmitPut(
        transactionId: transactionId,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Approve a transaction (pending -> approved).
  Future<TransactionResponse?> approveTransaction(int transactionId) async {
    try {
      final response = await _client.transactions
          .approveTransactionApiV1TransactionsTransactionIdApprovePut(
        transactionId: transactionId,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Reject a transaction (pending -> rejected).
  Future<TransactionResponse?> rejectTransaction(int transactionId) async {
    try {
      final response = await _client.transactions
          .rejectTransactionApiV1TransactionsTransactionIdRejectPut(
        transactionId: transactionId,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Draft a transaction (back to draft).
  Future<TransactionResponse?> draftTransaction(int transactionId) async {
    try {
      final response = await _client.transactions
          .draftTransactionApiV1TransactionsTransactionIdDraftPut(
        transactionId: transactionId,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }
}

