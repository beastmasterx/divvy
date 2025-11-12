// Main entry point for the Divvy CLI application.

import 'dart:io';
import 'package:cli/src/api/divvy_client.dart';
import 'package:cli/src/ui/menu.dart';
import 'package:cli/src/utils/i18n.dart';

const String version = '0.0.1';

/// Main function
Future<void> main(List<String> arguments) async {
  // Initialize language
  setLanguage();

  // Initialize API client
  final client = DivvyClient();

  // Show startup message
  print('Divvy Expense Splitter CLI v$version');
  print('Connecting to API at: ${client.baseUrl}');
  print('');

  // Run the menu loop
  try {
    await runMenu(client);
  } catch (e) {
    print('\nFatal error: $e');
    exit(1);
  }
}
