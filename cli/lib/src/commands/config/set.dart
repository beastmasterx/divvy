// Config set command.

import '../../models/session.dart';
import '../../utils/errors.dart';
import '../../utils/i18n.dart';
import '../../utils/terminal.dart';
import '../base/command.dart';

/// Config set command - sets a preference value.
class ConfigSetCommand extends Command {
  @override
  String get description => translate('Set Preference');

  @override
  bool canExecute(Session session) => true;

  @override
  Future<int> execute(CommandContext context, {List<String>? args}) async {
    try {
      if (args == null || args.isEmpty) {
        print('Error: Preference key required');
        print('Usage: divvy config set <key> [value]');
        print('');
        print('Available keys: apiUrl, language');
        return 1;
      }

      final key = args[0];
      final value = args.length > 1 ? args[1] : null;

      switch (key.toLowerCase()) {
        case 'apiurl':
        case 'api_url':
          if (value == null || value.isEmpty) {
            print('Error: Value required for apiUrl');
            return 1;
          }
          context.config.preferences.setApiUrl(value);
          print('apiUrl set to: $value');
          break;
        case 'language':
        case 'lang':
          if (value == null || value.isEmpty) {
            print('Error: Value required for language');
            return 1;
          }
          context.config.preferences.setLanguage(value);
          print('language set to: $value');
          break;
        case 'defaultgroupid':
        case 'default_group_id':
          if (value == null || value.isEmpty) {
            context.config.preferences.setDefaultGroup(null);
            print('defaultGroupId unset');
          } else {
            final id = int.tryParse(value);
            if (id == null) {
              print('Error: defaultGroupId must be a number');
              return 1;
            }
            context.config.preferences.setDefaultGroup(id);
            print('defaultGroupId set to: $id');
          }
          break;
        default:
          print('Error: Unknown or read-only preference key: $key');
          print('Available keys: apiUrl, language, defaultGroupId');
          return 1;
      }

      // Save preferences
      await context.config.preferences.save();
      return 0;
    } catch (e) {
      ensureTerminalState();
      print('Error: ${formatApiError(e)}');
      return 1;
    }
  }
}
