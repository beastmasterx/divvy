// Config get command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Config get command - gets a preference value.
class ConfigGetCommand extends Command {
  @override
  String get description => translate('Get Preference');

  @override
  bool canExecute(Session session) => true;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      if (args == null || args.isEmpty) {
        print('Error: Preference key required');
        print('Usage: divvy config get <key>');
        print('');
        print('Available keys: apiUrl, language, defaultGroupId, lastActiveGroupId, lastActivePeriodId');
        return 1;
      }

      final key = args[0];
      String? value;

      switch (key.toLowerCase()) {
        case 'apiurl':
        case 'api_url':
          value = context.config.apiUrl;
          break;
        case 'language':
        case 'lang':
          value = context.config.language;
          break;
        case 'defaultgroupid':
        case 'default_group_id':
          value = context.config.defaultGroupId?.toString() ?? 'not set';
          break;
        case 'lastactivegroupid':
        case 'last_active_group_id':
          value = context.config.lastActiveGroupId?.toString() ?? 'not set';
          break;
        case 'lastactiveperiodid':
        case 'last_active_period_id':
          value = context.config.lastActivePeriodId?.toString() ?? 'not set';
          break;
        default:
          print('Error: Unknown preference key: $key');
          print('Available keys: apiUrl, language, defaultGroupId, lastActiveGroupId, lastActivePeriodId');
          return 1;
      }

      print(value);
      return 0;
    } catch (e) {
      ensureTerminalState();
      print('Error: ${formatApiError(e)}');
      return 1;
    }
  }
}
