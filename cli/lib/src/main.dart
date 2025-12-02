// Main application entry point and initialization.

import 'dart:io';

import 'api/client.dart';
import 'auth/auth.dart';
import 'auth/token.dart';
import 'commands/auth.dart';
import 'commands/group.dart';
import 'commands/period.dart';
import 'commands/settlement.dart';
import 'commands/transaction.dart';
import 'config/config.dart';
import 'models/session.dart';
import 'services/category.dart';
import 'services/group.dart';
import 'services/period.dart';
import 'services/transaction.dart';
import 'services/user.dart';
import 'ui/menu.dart';
import 'utils/errors.dart';
import 'utils/i18n.dart';

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
    auth = Auth(client.authentication, tokenStorage);

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
  }

  /// Run the main menu loop.
  Future<void> run() async {
    print('Divvy Expense Splitter CLI v0.0.1');
    print('Connecting to API at: ${config.apiUrl}');
    print('');

    while (true) {
      showMenu(session);
      final maxChoice = getMaxChoice(session);
      final choice = getMenuChoice(maxChoice);

      if (choice == null) {
        print(translate('Invalid choice, please try again.'));
        continue;
      }

      try {
        if (!session.isAuthenticated) {
          // Unauthenticated menu
          switch (choice) {
            case 1:
              final success = await handleLogin(auth);
              if (success) {
                session.isAuthenticated = true;
                // Fetch and set user info
                final user = await userService.getCurrentUser();
                if (user != null) {
                  session.setUser(user.name, user.email);
                }
              }
              break;
            case 2:
              final success = await handleRegister(auth);
              if (success) {
                session.isAuthenticated = true;
                // Fetch and set user info
                final user = await userService.getCurrentUser();
                if (user != null) {
                  session.setUser(user.name, user.email);
                }
              }
              break;
            case 3:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else if (session.currentGroupId == null) {
          // Authenticated, no group
          switch (choice) {
            case 1:
              await handleSelectGroup(groupService, session);
              if (session.currentGroupId != null) {
                config.preferences.setLastActiveGroup(session.currentGroupId!);
                await config.preferences.save();
              }
              break;
            case 2:
              await handleCreateGroup(groupService, session);
              if (session.currentGroupId != null) {
                config.preferences.setLastActiveGroup(session.currentGroupId!);
                await config.preferences.save();
              }
              break;
            case 3:
              // TODO: Handle settings
              break;
            case 4:
              // Show "More" submenu
              await _handleMoreMenu(session);
              break;
            case 5:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else if (session.currentPeriodId == null) {
          // Authenticated with group, no period
          switch (choice) {
            case 1:
              await handleViewPeriod(periodService, session);
              break;
            case 2:
              await handleCreatePeriod(client, periodService, session);
              if (session.currentPeriodId != null) {
                config.preferences.setLastActivePeriod(session.currentPeriodId!);
                await config.preferences.save();
              }
              break;
            case 3:
              await handleSelectGroup(groupService, session);
              if (session.currentGroupId != null) {
                config.preferences.setLastActiveGroup(session.currentGroupId!);
                await config.preferences.save();
              }
              break;
            case 4:
              // TODO: Handle settings
              break;
            case 5:
              // Show "More" submenu
              await _handleMoreMenu(session);
              break;
            case 6:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else {
          // Authenticated with group and period - full menu
          switch (choice) {
            case 1:
              await handleViewTransactions(periodService, session);
              break;
            case 2:
              await handleAddTransaction(transactionService, periodService, categoryService, session);
              break;
            case 3:
              await handleViewBalances(periodService, session);
              break;
            case 4:
              await handleViewPeriod(periodService, session);
              break;
            case 5:
              await handleSelectGroup(groupService, session);
              if (session.currentGroupId != null) {
                config.preferences.setLastActiveGroup(session.currentGroupId!);
                await config.preferences.save();
              }
              break;
            case 6:
              await handleCreatePeriod(client, periodService, session);
              if (session.currentPeriodId != null) {
                config.preferences.setLastActivePeriod(session.currentPeriodId!);
                await config.preferences.save();
              }
              break;
            case 7:
              // Show "More" submenu
              await _handleMoreMenu(session);
              break;
            case 8:
              // TODO: Handle settings
              break;
            case 9:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        }
      } catch (e) {
        // Ensure terminal is in a clean state before printing errors
        _ensureTerminalState();
        print(formatApiError(e));
      }
    }
  }

  /// Ensure terminal is in a clean, usable state.
  /// This is important after password input or other raw mode operations.
  void _ensureTerminalState() {
    try {
      // Force restore terminal to safe defaults
      stdin.echoMode = true;
      stdin.lineMode = true;
      stdout.flush();
    } catch (_) {
      // Ignore errors - terminal might already be in correct state
    }
  }

  /// Handle the "More" submenu.
  Future<void> _handleMoreMenu(Session session) async {
    while (true) {
      showMoreMenu(session);
      final maxChoice = getMoreMenuMaxChoice(session);
      final choice = getMenuChoice(maxChoice);

      if (choice == null) {
        print(translate('Invalid choice, please try again.'));
        continue;
      }

      try {
        if (session.currentGroupId == null) {
          // No group selected
          switch (choice) {
            case 1:
              await handleLogout(auth);
              session.clear();
              return; // Exit submenu
            case 2:
              return; // Back to main menu
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else if (session.currentPeriodId == null) {
          // Group selected, no period
          switch (choice) {
            case 1:
              await handleCreateGroup(groupService, session);
              if (session.currentGroupId != null) {
                config.preferences.setLastActiveGroup(session.currentGroupId!);
                await config.preferences.save();
              }
              return; // Exit submenu after action
            case 2:
              await handleLogout(auth);
              session.clear();
              return; // Exit submenu
            case 3:
              return; // Back to main menu
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else {
          // Full context
          switch (choice) {
            case 1:
              await handleCreateGroup(groupService, session);
              if (session.currentGroupId != null) {
                config.preferences.setLastActiveGroup(session.currentGroupId!);
                await config.preferences.save();
              }
              return; // Exit submenu after action
            case 2:
              await handleViewSettlementPlan(periodService, session);
              break; // Stay in submenu
            case 3:
              await handleApplySettlement(periodService, session);
              break; // Stay in submenu
            case 4:
              await handleLogout(auth);
              session.clear();
              return; // Exit submenu
            case 5:
              return; // Back to main menu
            default:
              print(translate('Invalid choice, please try again.'));
          }
        }
      } catch (e) {
        // Ensure terminal is in a clean state before printing errors
        _ensureTerminalState();
        print(formatApiError(e));
      }
    }
  }
}
