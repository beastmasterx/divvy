// Base command interface.

import '../../models/session.dart';
import 'context.dart';

export 'context.dart';

/// Abstract base class for all menu commands.
abstract class Command {
  /// Human-readable description of the command (displayed in menu).
  String get description;

  /// Execute the command.
  Future<void> execute(CommandContext context);

  /// Check if this command is available/executable for the given session.
  /// Override this method to add availability conditions.
  bool canExecute(Session session) => true;
}
