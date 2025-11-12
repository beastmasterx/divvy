// Interactive UI selectors for user input.
//
// Provides functions for selecting items from lists, members, periods, and categories.

import 'dart:io';
import '../utils/i18n.dart';

/// Select an item from a list by number.
///
/// Parameters:
/// - [items]: List of items (maps with a name key)
/// - [nameKey]: Key to use for displaying item names
/// - [prompt]: Prompt text for the selection
///
/// Returns:
/// The selected item, or null if cancelled or empty list
T? selectFromList<T>(List<T> items, String Function(T) getName, String prompt) {
  if (items.isEmpty) {
    print(translate('No {} available.', [prompt.toLowerCase()]));
    return null;
  }

  print(translate('\n--- Select {} ---', [prompt]));
  for (var i = 0; i < items.length; i++) {
    print('${i + 1}. ${getName(items[i])}');
  }
  print(translate('------------------------'));

  while (true) {
    try {
      stdout.write(translate('Enter your choice (1-{}): ', [items.length]));
      final choice = stdin.readLineSync()?.trim() ?? '';

      if (choice.isEmpty) {
        print(translate('Input cannot be empty. Please enter a number.'));
        continue;
      }

      final index = int.parse(choice) - 1;
      if (index >= 0 && index < items.length) {
        return items[index];
      } else {
        print(
          translate('Invalid choice. Please enter a number between 1 and {}.', [
            items.length,
          ]),
        );
      }
    } on FormatException {
      print(translate('Invalid input. Please enter a number.'));
    } catch (e) {
      // Handle Ctrl+C or other interruptions
      if (e is! FormatException) {
        return null;
      }
      rethrow;
    }
  }
}

/// Select a period from all periods, with current period as default.
///
/// Parameters:
/// - [periods]: List of periods (with id, name, startDate, isSettled)
/// - [currentPeriodId]: ID of the current active period (optional)
///
/// Returns:
/// The selected period, or null if cancelled
T? selectPeriod<T>({
  required List<T> periods,
  required int? Function(T) getId,
  required String Function(T) getName,
  required DateTime Function(T) getStartDate,
  required bool Function(T) getIsSettled,
  int? currentPeriodId,
}) {
  if (periods.isEmpty) {
    print(translate('No periods available.'));
    return null;
  }

  // Create display strings for periods
  final periodsWithDisplay = periods.map((p) {
    final startDate = getStartDate(p);
    final dateOnly =
        '${startDate.year}-${startDate.month.toString().padLeft(2, '0')}-${startDate.day.toString().padLeft(2, '0')}';
    final status = getIsSettled(p) ? translate('Settled') : translate('Active');
    final isCurrent = currentPeriodId != null && getId(p) == currentPeriodId;
    final marker = isCurrent ? translate(' [Current]') : '';
    final displayName = '${getName(p)} ($dateOnly, $status)$marker';
    return (period: p, displayName: displayName, id: getId(p));
  }).toList();

  // Sort so current period appears first
  if (currentPeriodId != null) {
    periodsWithDisplay.sort((a, b) {
      if (a.id == currentPeriodId && b.id != currentPeriodId) return -1;
      if (a.id != currentPeriodId && b.id == currentPeriodId) return 1;
      return (b.id ?? 0).compareTo(a.id ?? 0); // Descending by ID
    });
  }

  print(translate('\n--- Select {} ---', [translate('Period')]));
  for (var i = 0; i < periodsWithDisplay.length; i++) {
    final defaultHint = (i == 0 && currentPeriodId != null) ? ' (default)' : '';
    print('${i + 1}. ${periodsWithDisplay[i].displayName}$defaultHint');
  }
  print(translate('------------------------'));

  while (true) {
    try {
      stdout.write(
        translate('Enter your choice (1-{}, or Enter for default): ', [
          periodsWithDisplay.length,
        ]),
      );
      final choice = stdin.readLineSync()?.trim() ?? '';

      if (choice.isEmpty) {
        // Empty input - return default (current period) if available
        if (currentPeriodId != null && periodsWithDisplay.isNotEmpty) {
          return periodsWithDisplay[0].period;
        }
        print(translate('Input cannot be empty. Please enter a number.'));
        continue;
      }

      final index = int.parse(choice) - 1;
      if (index >= 0 && index < periodsWithDisplay.length) {
        return periodsWithDisplay[index].period;
      } else {
        print(
          translate('Invalid choice. Please enter a number between 1 and {}.', [
            periodsWithDisplay.length,
          ]),
        );
      }
    } on FormatException {
      print(translate('Invalid input. Please enter a number.'));
    } catch (e) {
      // Handle Ctrl+C or other interruptions
      if (e is! FormatException) {
        return null;
      }
      rethrow;
    }
  }
}

/// Select a payer from active members.
///
/// For deposits, includes virtual member (Group) as an option for public fund.
/// For expenses, only shows regular active members.
///
/// Parameters:
/// - [members]: List of active members
/// - [forExpense]: If true, exclude virtual member (for expenses)
/// - [virtualMemberName]: Internal name of virtual member (default: "_system_group_")
/// - [virtualMemberDisplayName]: Display name for virtual member (default: "Group")
///
/// Returns:
/// The selected member name, or null if cancelled
String? selectPayer({
  required List<({int id, String name})> members,
  bool forExpense = false,
  String virtualMemberName = '_system_group_',
  String virtualMemberDisplayName = 'Group',
}) {
  if (members.isEmpty) {
    print(translate('No active members available.'));
    return null;
  }

  // Convert to list of maps for selectFromList
  final membersList = members.map((m) => {'id': m.id, 'name': m.name}).toList();

  // For deposits, add virtual member as an option for public fund
  if (!forExpense) {
    // Add virtual member option
    final virtualMember = {
      'id': -1, // Special ID for virtual member
      'name': virtualMemberDisplayName,
    };
    final membersWithGroup = [...membersList, virtualMember];

    final selected = selectFromList<Map<String, dynamic>>(
      membersWithGroup,
      (item) => item['name'] as String,
      translate('Payer'),
    );

    if (selected == null) {
      return null;
    }

    // Return internal name if virtual member selected
    if (selected['id'] == -1) {
      return virtualMemberName;
    }
    return selected['name'] as String;
  }

  // For expenses, only regular members
  final selected = selectFromList<Map<String, dynamic>>(
    membersList,
    (item) => item['name'] as String,
    translate('Payer'),
  );

  return selected?['name'] as String?;
}

/// Select a category from available categories.
///
/// Parameters:
/// - [categories]: List of categories (with id and name)
///
/// Returns:
/// The selected category name, or null if cancelled
String? selectCategory({required List<({int id, String name})> categories}) {
  if (categories.isEmpty) {
    print(translate('No {} available.', [translate('Category').toLowerCase()]));
    return null;
  }

  // Convert to list for selectFromList
  final categoriesList = categories
      .map(
        (c) => {
          'id': c.id,
          'name': c.name,
          'displayName': translateCategory(c.name), // Translated name
        },
      )
      .toList();

  final selected = selectFromList<Map<String, dynamic>>(
    categoriesList,
    (item) => item['displayName'] as String,
    translate('Category'),
  );

  // Return original name (not translated) for API
  return selected?['name'] as String?;
}
