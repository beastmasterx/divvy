// Menu input functions.

import 'dart:io';

import '../../models/session.dart';

/// Get menu choice from user input.
int? getMenuChoice(int maxChoice) {
  final input = stdin.readLineSync()?.trim();
  if (input == null || input.isEmpty) {
    return null;
  }
  final choice = int.tryParse(input);
  if (choice == null || choice < 1 || choice > maxChoice) {
    return null;
  }
  return choice;
}

/// Get the maximum menu choice number based on session context.
int getMaxChoice(Session session) {
  if (!session.isAuthenticated) {
    return 3; // Login, Register, Exit
  } else if (session.currentGroupId == null) {
    return 4; // Select Group, Create Group, More, Exit
  } else if (session.currentPeriodId == null) {
    return 4; // Select Period, Create Period, More, Exit
  } else if (session.currentTransactionId == null) {
    return 4; // View Transactions, View Balances, More, Exit
  } else {
    return 7; // Transaction level menu
  }
}

/// Get the maximum choice for the "More" submenu.
int getMoreMenuMaxChoice(Session session) {
  if (session.currentGroupId == null) {
    return 4; // Settings, Logout, Back to Top, Exit
  } else if (session.currentPeriodId == null) {
    return 4; // Settings, Logout, Back to Top, Exit
  } else if (session.currentTransactionId == null) {
    return 7; // Select Transaction, Add Transaction, View Settlement Plan, Settings, Logout, Back to Top, Exit
  } else {
    return 6; // Delete, Submit, Settings, Logout, Back to Top, Exit
  }
}
