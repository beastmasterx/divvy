// Base command interface.

import '../../models/session.dart';
import 'context.dart';

export 'context.dart';

/// Abstract base class for all commands.
abstract class Command {
  /// Human-readable description of the command.
  String get description;

  /// Execute the command with optional CLI arguments.
  ///
  /// Returns exit code: 0 for success, non-zero for failure.
  /// If args is null or empty, command should prompt interactively.
  Future<int> execute(CommandContext context, {List<String>? args});

  /// Check if this command is available/executable for the given session.
  /// Override this method to add availability conditions.
  bool canExecute(Session session) => true;
}
