// Menu display functions.

import '../../models/session.dart';
import '../../utils/i18n.dart';

/// Show the main menu based on current session context.
void showMenu(Session session) {
  // Build title with context: "Divvy Expense Splitter (user | group | period)"
  final parts = <String>[];
  if (session.userName != null) {
    parts.add(session.userName!);
  }
  if (session.currentGroupName != null) {
    parts.add(session.currentGroupName!);
  }
  if (session.currentPeriodName != null) {
    parts.add(session.currentPeriodName!);
  }

  final title = translate('Divvy Expense Splitter');
  if (parts.isNotEmpty) {
    print('\n$title (${parts.join(' | ')})');
  } else {
    print('\n$title');
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
    print(translate('3. More...'));
    print(translate('4. Exit'));
  } else if (session.currentPeriodId == null) {
    // Authenticated with group, but no period selected
    print(translate('1. Select Period'));
    print(translate('2. Create Period'));
    print(translate('3. More...'));
    print(translate('4. Exit'));
  } else if (session.currentTransactionId == null) {
    // Authenticated with group and period - period level
    print(translate('1. View Transactions'));
    print(translate('2. View Balances'));
    print(translate('3. More...'));
    print(translate('4. Exit'));
  } else {
    // Authenticated with group, period, and transaction - transaction level
    print(translate('1. View Details'));
    print(translate('2. Approve'));
    print(translate('3. Reject'));
    print(translate('4. Edit (draft only)'));
    print(translate('5. Back to Transactions'));
    print(translate('6. More...'));
    print(translate('7. Exit'));
  }
  print(translate('Enter your choice: '));
}

/// Show the "More" submenu.
void showMoreMenu(Session session) {
  print('\n${translate('More Options')}');
  print('---');

  if (session.currentGroupId == null) {
    // No group selected
    print(translate('1. Settings'));
    print(translate('2. Logout'));
    print(translate('3. Back to Top'));
    print(translate('4. Exit'));
  } else if (session.currentPeriodId == null) {
    // Group selected, no period
    print(translate('1. Settings'));
    print(translate('2. Logout'));
    print(translate('3. Back to Top'));
    print(translate('4. Exit'));
  } else if (session.currentTransactionId == null) {
    // Period level - full context
    print(translate('1. Select Transaction'));
    print(translate('2. Add Transaction'));
    print(translate('3. View Settlement Plan'));
    print(translate('4. Settings'));
    print(translate('5. Logout'));
    print(translate('6. Back to Top'));
    print(translate('7. Exit'));
  } else {
    // Transaction level
    print(translate('1. Delete (draft only)'));
    print(translate('2. Submit (draft only)'));
    print(translate('3. Settings'));
    print(translate('4. Logout'));
    print(translate('5. Back to Top'));
    print(translate('6. Exit'));
  }
  print(translate('Enter your choice: '));
}
