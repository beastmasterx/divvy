// Terminal utility functions.

import 'dart:io';

/// Ensure terminal is in a clean, usable state.
/// This is important after password input or other raw mode operations.
void ensureTerminalState() {
  try {
    // Force restore terminal to safe defaults
    stdin.echoMode = true;
    stdin.lineMode = true;
    stdout.flush();
  } catch (_) {
    // Ignore errors - terminal might already be in correct state
  }
}

