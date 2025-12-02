// Menu class for displaying and managing command menus.

import 'base/command.dart';

/// Menu that displays commands and handles user selection.
class Menu {
  final List<Command> commands;

  Menu(this.commands);

  /// Display the menu with numbered options.
  void display() {
    for (int i = 0; i < commands.length; i++) {
      print('${i + 1}. ${commands[i].description}');
    }
  }

  /// Get command for the given choice (1-based index).
  Command? getCommand(int choice) {
    if (choice < 1 || choice > commands.length) {
      return null;
    }
    return commands[choice - 1];
  }

  /// Get maximum valid choice number.
  int get maxChoice => commands.length;
}
