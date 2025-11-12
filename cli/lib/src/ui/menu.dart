// Menu system for the CLI application.

import 'dart:io';
import '../api/divvy_client.dart';
import '../services/members.dart';
import '../services/periods.dart';
import '../services/transactions.dart';
import '../services/settlement.dart';
import '../services/categories.dart';
import '../utils/i18n.dart';
import '../utils/validation.dart';
import 'selectors.dart';
import 'displays.dart';

/// Show the main menu.
void showMenu(String? currentPeriodName) {
  print(translate('\n--- Divvy Expense Splitter ---'));
  print(
    translate('Current Period: {}', [currentPeriodName ?? translate('None')]),
  );
  print(translate('1. Add Expense'));
  print(translate('2. Add Deposit'));
  print(translate('3. Add Refund'));
  print(translate('4. View Period'));
  print(translate('5. Close period'));
  print(translate('6. Add member'));
  print(translate('7. Remove Member'));
  print(translate('8. Exit'));
  print(translate('-----------------------------'));
}

/// Handle menu option 1: Add Expense
Future<void> handleAddExpense(DivvyClient client) async {
  stdout.write(translate('Enter expense description (optional): '));
  final description = stdin.readLineSync()?.trim() ?? '';

  stdout.write(translate('Enter total amount: '));
  final amountStr = stdin.readLineSync()?.trim() ?? '';

  if (amountStr.isEmpty) {
    print(translate('Error: Amount cannot be empty.'));
    return;
  }

  final amountValidation = validateAmount(amountStr);
  if (!amountValidation.isValid) {
    print(amountValidation.errorMessage);
    return;
  }

  // Ask for expense type
  stdout.write(
    translate(
      'Expense type - (s)hared, (p)ersonal, or (i)ndividual split? (default: i): ',
    ),
  );
  final expenseTypeInput = stdin.readLineSync()?.trim().toLowerCase() ?? 'i';

  String? payerName;
  bool isPersonal = false;
  String? expenseType;

  if (expenseTypeInput == 's' || expenseTypeInput == 'shared') {
    payerName = '_system_group_'; // Virtual member for shared expenses
    isPersonal = false;
    expenseType = 'shared';
  } else if (expenseTypeInput == 'p' || expenseTypeInput == 'personal') {
    final activeMembers = await listMembers(client, activeOnly: true);
    final membersList = activeMembers
        .map((m) => (id: m.id, name: m.name))
        .toList();
    final selected = selectPayer(members: membersList, forExpense: true);
    if (selected == null) {
      print(translate('Expense recording cancelled.'));
      return;
    }
    payerName = selected;
    isPersonal = true;
    expenseType = 'personal';
  } else {
    // individual (default)
    final activeMembers = await listMembers(client, activeOnly: true);
    final membersList = activeMembers
        .map((m) => (id: m.id, name: m.name))
        .toList();
    final selected = selectPayer(members: membersList, forExpense: true);
    if (selected == null) {
      print(translate('Expense recording cancelled.'));
      return;
    }
    payerName = selected;
    isPersonal = false;
    expenseType = 'individual';
  }

  // Select category
  final categories = await listCategories(client);
  final categoriesList = categories
      .map((c) => (id: c.id, name: c.name))
      .toList();
  final categoryName = selectCategory(categories: categoriesList);
  if (categoryName == null) {
    print(translate('Expense recording cancelled.'));
    return;
  }

  try {
    final result = await createExpense(
      client,
      amountStr,
      payerName,
      categoryName,
      description: description.isEmpty ? null : description,
      isPersonal: isPersonal,
      expenseType: expenseType,
    );
    print(result);
  } catch (e) {
    print('Error: ${client.handleError(e)}');
  }
}

/// Handle menu option 2: Add Deposit
Future<void> handleAddDeposit(DivvyClient client) async {
  stdout.write(translate('Enter deposit description (optional): '));
  final description = stdin.readLineSync()?.trim() ?? '';

  stdout.write(translate('Enter deposit amount: '));
  final amountStr = stdin.readLineSync()?.trim() ?? '';

  if (amountStr.isEmpty) {
    print(translate('Error: Amount cannot be empty.'));
    return;
  }

  final amountValidation = validateAmount(amountStr);
  if (!amountValidation.isValid) {
    print(amountValidation.errorMessage);
    return;
  }

  final activeMembers = await listMembers(client, activeOnly: true);
  final membersList = activeMembers
      .map((m) => (id: m.id, name: m.name))
      .toList();
  final payerName = selectPayer(members: membersList, forExpense: false);
  if (payerName == null) {
    print(translate('Deposit recording cancelled.'));
    return;
  }

  try {
    final result = await createDeposit(
      client,
      amountStr,
      payerName,
      description: description.isEmpty ? null : description,
    );
    print(result);
  } catch (e) {
    print('Error: ${client.handleError(e)}');
  }
}

/// Handle menu option 3: Add Refund
Future<void> handleAddRefund(DivvyClient client) async {
  final allMembers = await listMembers(client, activeOnly: false);
  final membersList = allMembers.map((m) => (id: m.id, name: m.name)).toList();

  if (membersList.isEmpty) {
    print(translate('No members available.'));
    return;
  }

  final selected = selectFromList<({int id, String name})>(
    membersList,
    (m) => m.name,
    translate('Member to refund'),
  );
  if (selected == null) {
    print(translate('Refund cancelled.'));
    return;
  }

  stdout.write(translate('Enter refund description (optional): '));
  final description = stdin.readLineSync()?.trim() ?? '';

  stdout.write(translate('Enter refund amount: '));
  final amountStr = stdin.readLineSync()?.trim() ?? '';

  if (amountStr.isEmpty) {
    print(translate('Error: Amount cannot be empty.'));
    return;
  }

  final amountValidation = validateAmount(amountStr);
  if (!amountValidation.isValid) {
    print(amountValidation.errorMessage);
    return;
  }

  try {
    final result = await createRefund(
      client,
      amountStr,
      selected.name,
      description: description.isEmpty ? null : description,
    );
    print(result);
  } catch (e) {
    print('Error: ${client.handleError(e)}');
  }
}

/// Handle menu option 4: View Period
Future<void> handleViewPeriod(DivvyClient client) async {
  final allPeriods = await listPeriods(client);
  final currentPeriod = await getCurrentPeriod(client);

  final selected = selectPeriod<Period>(
    periods: allPeriods,
    getId: (p) => p.id,
    getName: (p) => p.name,
    getStartDate: (p) => p.startDate,
    getIsSettled: (p) => p.isSettled,
    currentPeriodId: currentPeriod?.id,
  );

  if (selected == null) {
    print(translate('Period selection cancelled.'));
    return;
  }

  try {
    final summary = await getPeriodSummary(client, periodId: selected.id);
    displayViewPeriod(summary);
  } catch (e) {
    print('Error: ${client.handleError(e)}');
  }
}

/// Handle menu option 5: Close Period
Future<void> handleClosePeriod(DivvyClient client) async {
  try {
    // Show current period status first
    final currentSummary = await getPeriodSummary(client);
    displayViewPeriod(currentSummary);

    // Show settlement plan
    final currentPeriod = await getCurrentPeriod(client);
    if (currentPeriod != null) {
      final settlementPlan = await getSettlementPlan(
        client,
        periodId: currentPeriod.id,
      );
      if (settlementPlan.isNotEmpty) {
        displaySettlementPlan(settlementPlan);
      } else {
        print(
          translate(
            '\nNo settlement transactions needed (all balances already zero).\n',
          ),
        );
      }
    }

    // Ask for confirmation
    stdout.write(translate('Close this period? (y/n): '));
    final response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
    if (response != 'y' && response != 'yes') {
      print(translate('Period closing cancelled.'));
      return;
    }

    // Get new period name
    stdout.write(
      translate('Enter name for new period (press Enter for auto-generated): '),
    );
    final periodName = stdin.readLineSync()?.trim();
    final finalPeriodName = periodName?.isEmpty ?? true ? null : periodName;

    final result = await settleCurrentPeriod(
      client,
      periodName: finalPeriodName,
    );
    print(result);
  } catch (e) {
    print('Error: ${client.handleError(e)}');
  }
}

/// Handle menu option 6: Add Member
Future<void> handleAddMember(DivvyClient client) async {
  stdout.write(translate('Enter the member\'s email: '));
  final email = stdin.readLineSync()?.trim() ?? '';

  if (email.isEmpty) {
    print(translate('Member email cannot be empty.'));
    return;
  }

  if (!validateEmail(email)) {
    print('Invalid email format.');
    return;
  }

  stdout.write(translate('Enter the member\'s name: '));
  final name = stdin.readLineSync()?.trim() ?? '';

  if (name.isEmpty) {
    print(translate('Member name cannot be empty.'));
    return;
  }

  final nameValidation = validateName(name);
  if (!nameValidation.isValid) {
    print(nameValidation.errorMessage);
    return;
  }

  // Check if member exists
  final existingMember = await getMemberByEmail(client, email);

  if (existingMember != null) {
    if (existingMember.isActive) {
      print(
        translate(
          'Error: Member with email \'{}\' already exists and is active.',
          [email],
        ),
      );
    } else {
      // Member is inactive - ask to rejoin
      stdout.write(
        translate('Member \'{}\' is inactive. Rejoin? (y/n): ', [
          existingMember.name,
        ]),
      );
      final response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
      if (response == 'y' || response == 'yes') {
        try {
          final result = await rejoinMember(client, existingMember.id);
          print(result);
        } catch (e) {
          print('Error: ${client.handleError(e)}');
        }
      } else {
        print(translate('Rejoin cancelled.'));
      }
    }
  } else {
    // New member - add normally
    try {
      final result = await createMember(client, email, name);
      print(result);
    } catch (e) {
      print('Error: ${client.handleError(e)}');
    }
  }
}

/// Handle menu option 7: Remove Member
Future<void> handleRemoveMember(DivvyClient client) async {
  final activeMembers = await listMembers(client, activeOnly: true);
  final membersList = activeMembers
      .map((m) => (id: m.id, name: m.name))
      .toList();

  if (membersList.isEmpty) {
    print(translate('No active members to remove.'));
    return;
  }

  // Show current period status first
  try {
    final currentSummary = await getPeriodSummary(client);
    displayViewPeriod(currentSummary);
  } catch (e) {
    // If period summary fails, continue anyway
  }

  final selected = selectFromList<({int id, String name})>(
    membersList,
    (m) => m.name,
    translate('Member to remove'),
  );
  if (selected == null) {
    print(translate('Member removal cancelled.'));
    return;
  }

  // Get member's current balance (from period summary)
  try {
    final currentSummary = await getPeriodSummary(client);
    final memberBalance = currentSummary.memberBalances
        .firstWhere(
          (b) => b.name == selected.name,
          orElse: () => (name: selected.name, balance: 0, paidRemainder: false),
        )
        .balance;

    final balanceFormatted = (memberBalance.abs() / 100.0).toStringAsFixed(2);
    final balanceSign = memberBalance >= 0 ? '+' : '-';
    final balanceDisplay = '$balanceSign\$$balanceFormatted';

    String response;
    if (memberBalance > 0) {
      print(
        translate('\n⚠️  Warning: \'{}\' is owed {}.', [
          selected.name,
          balanceDisplay,
        ]),
      );
      print(
        translate(
          '   Other members should settle this balance before removal.',
        ),
      );
      stdout.write(
        translate('Remove member \'{}\' anyway? (y/n): ', [selected.name]),
      );
      response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
    } else if (memberBalance < 0) {
      print(
        translate('\n⚠️  Warning: \'{}\' owes {}.', [
          selected.name,
          balanceDisplay,
        ]),
      );
      print(translate('   This balance should be settled before removal.'));
      stdout.write(
        translate('Remove member \'{}\' anyway? (y/n): ', [selected.name]),
      );
      response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
    } else {
      stdout.write(
        translate('Remove member \'{}\' (Balance: \$0.00)? (y/n): ', [
          selected.name,
        ]),
      );
      response = stdin.readLineSync()?.trim().toLowerCase() ?? '';
    }

    if (response != 'y' && response != 'yes') {
      print(translate('Member removal cancelled.'));
      return;
    }

    final result = await removeMember(client, selected.id);
    print(result);
  } catch (e) {
    print('Error: ${client.handleError(e)}');
  }
}

/// Main menu loop
Future<void> runMenu(DivvyClient client) async {
  while (true) {
    try {
      String? periodName;
      try {
        final currentPeriod = await getCurrentPeriod(client);
        periodName = currentPeriod?.name;
      } catch (e) {
        // Silently handle errors loading period name - show placeholder
        // Full error will be shown if user tries to use period-dependent features
        periodName = translate('Not available');
      }
      showMenu(periodName ?? translate('Initializing...'));

      stdout.write(translate('Enter your choice: '));
      final choice = stdin.readLineSync()?.trim() ?? '';

      switch (choice) {
        case '1':
          await handleAddExpense(client);
          break;
        case '2':
          await handleAddDeposit(client);
          break;
        case '3':
          await handleAddRefund(client);
          break;
        case '4':
          await handleViewPeriod(client);
          break;
        case '5':
          await handleClosePeriod(client);
          break;
        case '6':
          await handleAddMember(client);
          break;
        case '7':
          await handleRemoveMember(client);
          break;
        case '8':
          print(translate('Exiting Divvy. Goodbye!'));
          return;
        default:
          print(translate('Invalid choice, please try again.'));
      }
    } catch (e) {
      // Handle all errors gracefully and continue the menu loop
      print('\n⚠️  ${client.handleError(e)}\n');
      // Wait a moment before showing menu again
      await Future.delayed(const Duration(milliseconds: 500));
    }
  }
}
