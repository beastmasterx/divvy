// Session state management.

/// Current application session state.
class Session {
  int? currentGroupId;
  String? currentGroupName;
  int? currentPeriodId;
  String? currentPeriodName;
  int? currentTransactionId;
  String? currentTransactionDescription;
  bool isAuthenticated = false;
  String? userName;
  String? userEmail;

  /// Clear session state.
  void clear() {
    currentGroupId = null;
    currentGroupName = null;
    currentPeriodId = null;
    currentPeriodName = null;
    currentTransactionId = null;
    currentTransactionDescription = null;
    isAuthenticated = false;
    userName = null;
    userEmail = null;
  }

  /// Set current group.
  void setGroup(int id, String name) {
    currentGroupId = id;
    currentGroupName = name;
    // Clear period when group changes
    currentPeriodId = null;
    currentPeriodName = null;
  }

  /// Set current period.
  void setPeriod(int id, String name) {
    currentPeriodId = id;
    currentPeriodName = name;
    // Clear transaction when period changes
    currentTransactionId = null;
    currentTransactionDescription = null;
  }

  /// Set current transaction.
  void setTransaction(int id, String? description) {
    currentTransactionId = id;
    currentTransactionDescription = description;
  }

  /// Set current user info.
  void setUser(String name, String email) {
    userName = name;
    userEmail = email;
  }
}
