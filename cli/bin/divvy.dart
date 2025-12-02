// Main entry point for Divvy CLI application.

import 'dart:io';

import 'package:cli/src/main.dart';

/// Main function.
Future<void> main(List<String> arguments) async {
  try {
    final app = App();
    await app.initialize();
    await app.run();
  } catch (e, stackTrace) {
    print('Fatal error: $e');
    print('Stack trace: $stackTrace');
    exit(1);
  }
}

