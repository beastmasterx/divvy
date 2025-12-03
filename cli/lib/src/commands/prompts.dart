// Input prompts and validation utilities.

import 'dart:io';

import '../utils/i18n.dart';
import '../utils/validation.dart';

/// Prompt for a string input.
String? promptString(String message, {bool required = true}) {
  stdout.write(translate(message));
  final input = stdin.readLineSync()?.trim();
  if (required && (input == null || input.isEmpty)) {
    return null;
  }
  return input;
}

/// Prompt for an integer input.
int? promptInt(String message, {bool required = true}) {
  stdout.write(translate(message));
  final input = stdin.readLineSync()?.trim();
  if (input == null || input.isEmpty) {
    return required ? null : 0;
  }
  return int.tryParse(input);
}

/// Prompt for a double/amount input.
double? promptAmount(String message, {bool required = true}) {
  stdout.write(translate(message));
  final input = stdin.readLineSync()?.trim();
  if (input == null || input.isEmpty) {
    return required ? null : 0.0;
  }
  return double.tryParse(input);
}

/// Prompt for yes/no confirmation.
bool promptYesNo(String message, {bool defaultYes = false}) {
  final defaultText = defaultYes ? 'Y/n' : 'y/N';
  stdout.write('${translate(message)} ($defaultText): ');
  final input = stdin.readLineSync()?.trim().toLowerCase();
  if (input == null || input.isEmpty) {
    return defaultYes;
  }
  return input == 'y' || input == 'yes';
}

/// Prompt for selection from a list.
int? promptSelection(String message, int maxChoice, {int? defaultChoice}) {
  final defaultText = defaultChoice != null ? ' (default: $defaultChoice)' : '';
  stdout.write('${translate(message)}$defaultText: ');
  final input = stdin.readLineSync()?.trim();

  if (input == null || input.isEmpty) {
    return defaultChoice;
  }

  final choice = int.tryParse(input);
  if (choice == null || choice < 1 || choice > maxChoice) {
    return null;
  }
  return choice;
}

/// Prompt for email with validation.
String? promptEmail({bool required = true}) {
  while (true) {
    final email = promptString('Email: ', required: required);
    if (email == null) {
      return required ? null : '';
    }
    if (validateEmail(email)) {
      return email;
    }
    print(translate('Invalid email address.'));
  }
}

/// Prompt for password (hidden input with asterisks).
String? promptPassword({bool required = true}) {
  stdout.write(translate('Password: '));

  String password = '';

  try {
    // Disable echo and line mode to read character by character
    stdin.echoMode = false;
    stdin.lineMode = false;

    // Read characters one by one and display asterisks
    while (true) {
      final char = stdin.readByteSync();

      // Enter key (13 = CR, 10 = LF)
      if (char == 13 || char == 10) {
        break;
      }

      // Backspace/Delete (8 = BS, 127 = DEL)
      if (char == 8 || char == 127) {
        if (password.isNotEmpty) {
          password = password.substring(0, password.length - 1);
          // Erase the asterisk: move back, write space, move back again
          stdout.write('\b \b');
        }
      }
      // Ctrl+C (3) or Ctrl+D (4) - exit
      else if (char == 3 || char == 4) {
        print('');
        return null;
      }
      // Printable ASCII characters (32-126)
      else if (char >= 32 && char <= 126) {
        password += String.fromCharCode(char);
        stdout.write('*');
      }
    }
  } catch (e) {
    // If raw mode fails (e.g., on some Windows terminals), fall back to simple hidden input
    try {
      stdin.echoMode = true;
      stdin.lineMode = true;
      final input = stdin.readLineSync()?.trim();
      if (required && (input == null || input.isEmpty)) {
        return null;
      }
      return input;
    } catch (_) {
      // Last resort: read normally (not secure, but at least it works)
      final input = stdin.readLineSync()?.trim();
      if (required && (input == null || input.isEmpty)) {
        return null;
      }
      return input;
    }
  } finally {
    // Restore terminal to safe defaults - ensures cursor is visible
    try {
      stdin.echoMode = true;
      stdin.lineMode = true;
      stdout.flush();
    } catch (_) {
      // Ignore errors
    }
  }

  print(''); // Newline after password input

  if (required && password.isEmpty) {
    return null;
  }
  return password;
}
