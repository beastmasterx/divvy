// Interactive menu system for the CLI.

import 'dart:io';

import '../models/session.dart';
import '../utils/i18n.dart';

/// Show the main menu based on current session context.
void showMenu(Session session) {
  print('\n${translate('Divvy Expense Splitter')}');
  if (session.currentGroupName != null) {
    print(translate('Current Group: {}', [session.currentGroupName!]));
  }
  if (session.currentPeriodName != null) {
    print(translate('Current Period: {}', [session.currentPeriodName!]));
  }
  print('');

  if (!session.isAuthenticated) {
    // Not authenticated - simple menu
    print(translate('1. Login'));
    print(translate('2. Register'));
    print(translate('3. Exit'));
  } else if (session.currentGroupId == null) {
    // Authenticated but no group selected
    print(translate('1. Select Group'));
    print(translate('2. Create Group'));
    print(translate('3. Settings'));
    print(translate('4. More...'));
    print(translate('5. Exit'));
  } else if (session.currentPeriodId == null) {
    // Authenticated with group, but no period selected
    print(translate('1. View Period'));
    print(translate('2. Create Period'));
    print(translate('3. Select Group'));
    print(translate('4. Settings'));
    print(translate('5. More...'));
    print(translate('6. Exit'));
  } else {
    // Authenticated with group and period - full menu (most common first)
    print(translate('1. View Transactions'));
    print(translate('2. Add Transaction'));
    print(translate('3. View Balances'));
    print(translate('4. View Period'));
    print(translate('5. Select Group'));
    print(translate('6. Create Period'));
    print(translate('7. More...'));
    print(translate('8. Settings'));
    print(translate('9. Exit'));
  }
  print(translate('Enter your choice: '));
}

/// Show the "More" submenu.
void showMoreMenu(Session session) {
  print('\n${translate('More Options')}');
  print('---');

  if (session.currentGroupId == null) {
    // No group selected
    print(translate('1. Logout'));
    print(translate('2. Back'));
  } else if (session.currentPeriodId == null) {
    // Group selected, no period
    print(translate('1. Create Group'));
    print(translate('2. Logout'));
    print(translate('3. Back'));
  } else {
    // Full context - show all less common options
    print(translate('1. Create Group'));
    print(translate('2. View Settlement Plan'));
    print(translate('3. Apply Settlement'));
    print(translate('4. Logout'));
    print(translate('5. Back'));
  }
  print(translate('Enter your choice: '));
}

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
    return 5; // Select Group, Create Group, Settings, More, Exit
  } else if (session.currentPeriodId == null) {
    return 6; // View Period, Create Period, Select Group, Settings, More, Exit
  } else {
    return 9; // Full menu
  }
}

/// Get the maximum choice for the "More" submenu.
int getMoreMenuMaxChoice(Session session) {
  if (session.currentGroupId == null) {
    return 2; // Logout, Back
  } else if (session.currentPeriodId == null) {
    return 3; // Create Group, Logout, Back
  } else {
    return 5; // Create Group, View Settlement Plan, Apply Settlement, Logout, Back
  }
}
