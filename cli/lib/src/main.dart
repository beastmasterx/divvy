// Main application entry point and initialization.

import 'api/client.dart';
import 'auth/auth.dart';
import 'auth/token.dart';
import 'commands/commands.dart';
import 'config/config.dart';
import 'models/session.dart';
import 'services/category.dart';
import 'services/group.dart';
import 'services/period.dart';
import 'services/transaction.dart';
import 'services/user.dart';
import 'utils/errors.dart';
import 'utils/i18n.dart';
import 'utils/terminal.dart';

/// Main application class.
class App {
  late final Config config;
  late final TokenStorage tokenStorage;
  late final Client client;
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
    client = Client(baseUrl: config.baseUrl, token: tokenStorage);

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

    // Load session state from preferences (if authenticated)
    if (session.isAuthenticated && config.lastActiveGroupId != null) {
      try {
        final group = await groupService.getGroup(config.lastActiveGroupId!);
        if (group != null) {
          session.setGroup(group.id, group.name);

          // Load period if available
          if (config.lastActivePeriodId != null) {
            final period = await periodService.getPeriod(config.lastActivePeriodId!);
            if (period != null && period.groupId == group.id) {
              session.setPeriod(period.id, period.name);
            }
          }
        }
      } catch (e) {
        // If loading fails, just continue without restoring session
        // This can happen if the group/period was deleted
      }
    }
  }

  /// Create command context.
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

  /// Run the CLI with command-line arguments.
  Future<int> run(List<String> args) async {
    try {
      if (args.isEmpty) {
        _printUsage();
        return 1;
      }

      final command = args[0];
      final remainingArgs = args.sublist(1);

      // Handle verb-first commands (general commands)
      switch (command) {
        case 'get':
          final getCommand = GetCommand(_createContext());
          return await getCommand.execute(remainingArgs);
        case 'create':
          final createCommand = CreateCommand(_createContext());
          return await createCommand.execute(remainingArgs);
        case 'edit':
          final editCommand = EditCommand(_createContext());
          return await editCommand.execute(remainingArgs);
        case 'delete':
          final deleteCommand = DeleteCommand(_createContext());
          return await deleteCommand.execute(remainingArgs);
        case 'apply':
          final applyCommand = ApplyCommand(_createContext());
          return await applyCommand.execute(remainingArgs);
        // Handle resource-specific commands (only for specific verbs)
        case 'auth':
          final authCommand = AuthCommand(_createContext());
          return await authCommand.execute(remainingArgs);
        case 'config':
          final configCommand = ConfigCommand(_createContext());
          return await configCommand.execute(remainingArgs);
        case 'period':
        case 'periods':
          final periodCommand = PeriodCommand(_createContext());
          return await periodCommand.execute(remainingArgs);
        case 'trans':
        case 'transaction':
        case 'transactions':
          final transactionCommand = TransactionCommand(_createContext());
          return await transactionCommand.execute(remainingArgs);
        // Handle utility commands
        case 'help':
        case '--help':
        case '-h':
          _printUsage();
          return 0;
        case 'version':
        case '--version':
          _printVersion();
          return 0;
        default:
          print('Unknown command: $command');
          print('Run "divvy help" for usage information.');
          return 1;
      }
    } catch (e) {
      ensureTerminalState();
      print('Error: ${formatApiError(e)}');
      return 1;
    }
  }

  void _printUsage() {
    print('Divvy Expense Splitter CLI');
    print('');
    print('Usage: divvy <command> [options]');
    print('');
    print('General Commands:');
    print('  get        Get resources (group, period, transaction)');
    print('  create     Create resources');
    print('  edit       Edit resources');
    print('  delete     Delete resources');
    print('  apply      Apply resources from YAML file');
    print('');
    print('Resource-Specific Commands:');
    print('  auth       Authentication commands (login, register, logout, status)');
    print('  config     Configuration management (view, set-context, get, set)');
    print('  period     Period-specific operations (close, balances, settlement)');
    print('  transaction Transaction-specific operations (approve, reject, submit)');
    print('');
    print('Utility Commands:');
    print('  help       Show this help message');
    print('  version    Show version information');
    print('');
    print('Examples:');
    print('  divvy get group');
    print('  divvy create group "My Group"');
    print('  divvy auth login');
    print('  divvy period close');
    print('');
    print('Run "divvy <command> --help" for more information on a command.');
  }

  void _printVersion() {
    print('Divvy CLI v0.0.1');
  }
}
