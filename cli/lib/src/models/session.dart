// Session state management.

/// Current application session state.
class Session {
  int? currentGroupId;
  String? currentGroupName;
  int? currentPeriodId;
  String? currentPeriodName;
  bool isAuthenticated = false;
  String? userName;
  String? userEmail;

  /// Clear session state.
  void clear() {
    currentGroupId = null;
    currentGroupName = null;
    currentPeriodId = null;
    currentPeriodName = null;
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
  }

  /// Set current user info.
  void setUser(String name, String email) {
    userName = name;
    userEmail = email;
  }
}
