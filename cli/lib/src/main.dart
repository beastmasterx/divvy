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
        // Automatically select the current active period for this group
        final currentPeriod = await groupService.getCurrentPeriod(group.id);
        if (currentPeriod != null) {
          session.setPeriod(currentPeriod.id, currentPeriod.name);
        }
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
              // Show "More" submenu
              await _handleMoreMenu(session);
              break;
            case 4:
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
              // Show "More" submenu
              await _handleMoreMenu(session);
              break;
            case 4:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else if (session.currentTransactionId == null) {
          // Authenticated with group and period - period level
          switch (choice) {
            case 1:
              await handleViewTransactions(periodService, session);
              break;
            case 2:
              await handleViewBalances(periodService, session);
              break;
            case 3:
              // Show "More" submenu
              await _handleMoreMenu(session);
              break;
            case 4:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else {
          // Authenticated with group, period, and transaction - transaction level
          switch (choice) {
            case 1:
              await handleViewTransactionDetails(transactionService, session);
              break;
            case 2:
              await handleApproveTransaction(transactionService, session);
              break;
            case 3:
              await handleRejectTransaction(transactionService, session);
              break;
            case 4:
              await handleEditTransaction(transactionService, periodService, categoryService, session);
              break;
            case 5:
              // Back to Transactions
              session.currentTransactionId = null;
              session.currentTransactionDescription = null;
              break;
            case 6:
              // Show "More" submenu
              await _handleMoreMenu(session);
              break;
            case 7:
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
              // TODO: Handle settings
              break;
            case 2:
              await handleLogout(auth);
              session.clear();
              return; // Exit submenu
            case 3:
              // Back to Top - clear all context
              session.currentGroupId = null;
              session.currentGroupName = null;
              session.currentPeriodId = null;
              session.currentPeriodName = null;
              session.currentTransactionId = null;
              session.currentTransactionDescription = null;
              return; // Exit submenu
            case 4:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else if (session.currentPeriodId == null) {
          // Group selected, no period
          switch (choice) {
            case 1:
              // TODO: Handle settings
              break;
            case 2:
              await handleLogout(auth);
              session.clear();
              return; // Exit submenu
            case 3:
              // Back to Top - clear all context
              session.currentGroupId = null;
              session.currentGroupName = null;
              session.currentPeriodId = null;
              session.currentPeriodName = null;
              session.currentTransactionId = null;
              session.currentTransactionDescription = null;
              return; // Exit submenu
            case 4:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else if (session.currentTransactionId == null) {
          // Period level - full context
          switch (choice) {
            case 1:
              await handleSelectTransaction(periodService, session);
              if (session.currentTransactionId != null) {
                return; // Exit submenu after selection
              }
              break;
            case 2:
              await handleAddTransaction(transactionService, periodService, categoryService, session);
              return; // Exit submenu after action
            case 3:
              await handleViewSettlementPlan(periodService, session);
              break; // Stay in submenu
            case 4:
              // TODO: Handle settings
              break;
            case 5:
              await handleLogout(auth);
              session.clear();
              return; // Exit submenu
            case 6:
              // Back to Top - clear all context
              session.currentGroupId = null;
              session.currentGroupName = null;
              session.currentPeriodId = null;
              session.currentPeriodName = null;
              session.currentTransactionId = null;
              session.currentTransactionDescription = null;
              return; // Exit submenu
            case 7:
              print(translate('Exiting Divvy. Goodbye!'));
              exit(0);
            default:
              print(translate('Invalid choice, please try again.'));
          }
        } else {
          // Transaction level
          switch (choice) {
            case 1:
              final transaction = await transactionService.getTransaction(session.currentTransactionId!);
              if (transaction?.status.toString().split('.').last == 'draft') {
                await handleDeleteTransaction(transactionService, session);
                if (session.currentTransactionId == null) {
                  return; // Exit submenu if transaction was deleted
                }
              } else {
                print(translate('Only draft transactions can be deleted.'));
              }
              break;
            case 2:
              final transaction = await transactionService.getTransaction(session.currentTransactionId!);
              if (transaction?.status.toString().split('.').last == 'draft') {
                await handleSubmitTransaction(transactionService, session);
              } else {
                print(translate('Only draft transactions can be submitted.'));
              }
              break;
            case 3:
              // TODO: Handle settings
              break;
            case 4:
              await handleLogout(auth);
              session.clear();
              return; // Exit submenu
            case 5:
              // Back to Top - clear all context
              session.currentGroupId = null;
              session.currentGroupName = null;
              session.currentPeriodId = null;
              session.currentPeriodName = null;
              session.currentTransactionId = null;
              session.currentTransactionDescription = null;
              return; // Exit submenu
            case 6:
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
}
