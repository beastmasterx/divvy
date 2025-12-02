// Command context for dependency injection.

import '../../api/client.dart';
import '../../auth/auth.dart';
import '../../config/config.dart';
import '../../models/session.dart';
import '../../services/category.dart';
import '../../services/group.dart';
import '../../services/period.dart';
import '../../services/transaction.dart';
import '../../services/user.dart';

/// Context object that provides commands with access to application dependencies.
class CommandContext {
  final Auth auth;
  final Session session;
  final Config config;
  final DivvyClient client;
  final GroupService groupService;
  final PeriodService periodService;
  final TransactionService transactionService;
  final CategoryService categoryService;
  final UserService userService;

  CommandContext({
    required this.auth,
    required this.session,
    required this.config,
    required this.client,
    required this.groupService,
    required this.periodService,
    required this.transactionService,
    required this.categoryService,
    required this.userService,
  });
}
