// Main application entry point and initialization.

import 'api/client.dart';
import 'auth/auth.dart';
import 'auth/token.dart';
import 'commands/commands.dart';
import 'commands/menu.dart';
import 'config/config.dart';
import 'menus/menus.dart';
import 'models/session.dart';
import 'services/category.dart';
import 'services/group.dart';
import 'services/period.dart';
import 'services/transaction.dart';
import 'services/user.dart';
import 'ui/menu/input.dart';
import 'utils/errors.dart';
import 'utils/i18n.dart';
import 'utils/terminal.dart';

/// Main application class.
class App {
  late final Config config;
  late final TokenStorage tokenStorage;
  late final DivvyClient client;
  late final Auth auth;
  late final Session session;

  late final GroupService groupService;
  late final PeriodService periodService;
  late final TransactionService transactionService;
  late final CategoryService categoryService;
  late final UserService userService;

  /// Initialize the application.
  Future<void> initialize() async {
    // Load configuration
    config = await Config.load();

    // Initialize i18n
    setLanguage(config.language);

    // Initialize token storage
    tokenStorage = TokenStorage();
    await tokenStorage.load();

    // Initialize API client
    client = DivvyClient(baseUrl: config.baseUrl, tokenStorage: tokenStorage);

    // Initialize authentication
    auth = Auth(client, tokenStorage);

    // Initialize session
    session = Session();
    session.isAuthenticated = auth.isAuthenticated;

    // Initialize services
    groupService = GroupService(client);
    periodService = PeriodService(client);
    transactionService = TransactionService(client);
    categoryService = CategoryService(client);
    userService = UserService(client);

    // If already authenticated, fetch user info
    if (session.isAuthenticated) {
      final user = await userService.getCurrentUser();
      if (user != null) {
        session.setUser(user.name, user.email);
      }
    }

    // Restore last active group/period from preferences
    if (config.lastActiveGroupId != null) {
      final group = await groupService.getGroup(config.lastActiveGroupId!);
      if (group != null) {
        session.setGroup(group.id, group.name);
      }
    }

    if (config.lastActivePeriodId != null) {
      final period = await periodService.getPeriod(config.lastActivePeriodId!);
      if (period != null) {
        session.setPeriod(period.id, period.name);
      }
    }
  }

  /// Create command context from current app state.
  CommandContext _createContext() {
    return CommandContext(
      auth: auth,
      session: session,
      config: config,
      client: client,
      groupService: groupService,
      periodService: periodService,
      transactionService: transactionService,
      categoryService: categoryService,
      userService: userService,
    );
  }

  /// Get menu for current session state.
  Menu _getMenu() {
    if (!session.isAuthenticated) {
      return UserMenu();
    } else if (session.currentGroupId == null) {
      return GroupMenu();
    } else if (session.currentPeriodId == null) {
      return PeriodMenu();
    } else if (session.currentTransactionId == null) {
      return TransactionMenu();
    } else {
      return TransactionDetailMenu();
    }
  }

  /// Get "More" menu for current session state.
  Menu _getMoreMenu() {
    if (session.currentGroupId == null) {
      return GroupMoreMenu();
    } else if (session.currentPeriodId == null) {
      return PeriodMoreMenu();
    } else if (session.currentTransactionId == null) {
      return TransactionMoreMenu();
    } else {
      return TransactionDetailMoreMenu();
    }
  }

  /// Run the main menu loop.
  Future<void> run() async {
    print('Divvy Expense Splitter (v0.0.1)');
    print('Connecting to API at: ${config.apiUrl}');
    print('');

    while (true) {
      // Show menu title
      _showMenuTitle();

      // Display menu
      final menu = _getMenu();
      menu.display();

      // Get user choice
      final choice = getMenuChoice(menu.maxChoice);
      if (choice == null) {
        print(translate('Invalid choice, please try again.'));
        continue;
      }

      try {
        final command = menu.getCommand(choice);
        if (command == null) {
          print(translate('Invalid choice, please try again.'));
          continue;
        }

        // Handle special "More" command
        if (command is MoreCommand) {
          await _handleMoreMenu();
          continue;
        }

        // Execute command
        if (command.canExecute(session)) {
          await command.execute(_createContext());
        } else {
          print(translate('Command not available.'));
        }
      } catch (e) {
        // Ensure terminal is in a clean state before printing errors
        ensureTerminalState();
        print(formatApiError(e));
      }
    }
  }

  /// Show menu title with context.
  void _showMenuTitle() {
    // Build title with context: "Divvy Expense Splitter (user | group | period)"
    final parts = <String>[];
    if (session.userName != null) {
      parts.add(session.userName!);
    }
    if (session.currentGroupName != null) {
      parts.add(session.currentGroupName!);
    }
    if (session.currentPeriodName != null) {
      parts.add(session.currentPeriodName!);
    }

    final title = translate('Divvy Expense Splitter');
    if (parts.isNotEmpty) {
      print('\n$title: ${parts.join(' > ')}');
    } else {
      print('\n$title');
    }
    print('');
  }

  /// Handle the "More" submenu.
  Future<void> _handleMoreMenu() async {
    while (true) {
      print('\n${translate('More Options')}');
      print('---');

      final menu = _getMoreMenu();
      menu.display();

      final choice = getMenuChoice(menu.maxChoice);
      if (choice == null) {
        print(translate('Invalid choice, please try again.'));
        continue;
      }

      try {
        final command = menu.getCommand(choice);
        if (command == null) {
          print(translate('Invalid choice, please try again.'));
          continue;
        }

        // Execute command
        if (command.canExecute(session)) {
          await command.execute(_createContext());

          // Check if we should exit submenu
          // Commands that clear transaction context or logout should exit
          if (command is LogoutCommand ||
              command is BackToTopCommand ||
              command is ExitCommand ||
              (command is SelectTransactionCommand && session.currentTransactionId != null) ||
              command is AddTransactionCommand ||
              (command is DeleteTransactionCommand && session.currentTransactionId == null)) {
            return; // Exit submenu
          }
        } else {
          print(translate('Command not available.'));
        }
      } catch (e) {
        // Ensure terminal is in a clean state before printing errors
        ensureTerminalState();
        print(formatApiError(e));
      }
    }
  }
}
