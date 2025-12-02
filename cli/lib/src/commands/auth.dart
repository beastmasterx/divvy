// Authentication commands.

import 'dart:io';

import '../auth/auth.dart';
import '../ui/prompts.dart';
import '../utils/i18n.dart';

/// Ensure terminal is in a clean, usable state.
void _ensureTerminalState() {
  try {
    stdin.echoMode = true;
    stdin.lineMode = true;
    stdout.flush();
  } catch (_) {
    // Ignore
  }
}

/// Handle login command.
Future<bool> handleLogin(Auth auth) async {
  try {
    final email = promptEmail();
    if (email == null) {
      print(translate('Login cancelled.'));
      return false;
    }

    final password = promptPassword();
    if (password == null) {
      print(translate('Login cancelled.'));
      return false;
    }

    print(translate('Logging in...'));
    final success = await auth.login(email, password);
    if (success) {
      print(translate('Login successful!'));
      return true;
    } else {
      print(translate('Invalid credentials.'));
      return false;
    }
  } catch (e) {
    _ensureTerminalState();
    rethrow;
  }
}

/// Handle register command.
Future<bool> handleRegister(Auth auth) async {
  try {
    final email = promptEmail();
    if (email == null) {
      print(translate('Registration cancelled.'));
      return false;
    }

    final name = promptString(translate('Name: '));
    if (name == null) {
      print(translate('Registration cancelled.'));
      return false;
    }

    final password = promptPassword();
    if (password == null) {
      print(translate('Registration cancelled.'));
      return false;
    }

    print(translate('Registering...'));
    final success = await auth.register(email, name, password);
    if (success) {
      print(translate('Registration successful!'));
      return true;
    } else {
      print(translate('Email already exists.'));
      return false;
    }
  } catch (e) {
    _ensureTerminalState();
    rethrow;
  }
}

/// Handle logout command.
Future<void> handleLogout(Auth auth) async {
  await auth.logout();
  print(translate('Logged out successfully.'));
}

