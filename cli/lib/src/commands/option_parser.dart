// Generic option argument parsing mixin.

/// Mixin that provides flexible option parsing capability.
mixin OptionParserMixin {
  /// Parse an option from arguments.
  ///
  /// [args] - Command line arguments
  /// [longName] - Long flag name (e.g., 'user', 'password', 'name')
  /// [shortName] - Short flag name (e.g., 'u', 'p', 'n'), optional
  /// [prompt] - Function to prompt if not found, optional
  ///
  /// Returns the parsed value, or null if not found and no prompt provided.
  String? parseOption(List<String>? args, {required String longName, String? shortName, String? Function()? prompt}) {
    if (args == null || args.isEmpty) {
      // No args, use prompt if provided
      return prompt?.call();
    }

    // Look for the option in args
    for (int i = 0; i < args.length; i++) {
      // Check long form: --option or --option=value
      if (args[i] == '--$longName') {
        if (i + 1 < args.length && !args[i + 1].startsWith('-')) {
          return args[i + 1];
        }
        // --option without value, use prompt if provided
        return prompt?.call();
      } else if (args[i].startsWith('--$longName=')) {
        return args[i].substring('--$longName='.length);
      }

      // Check short form: -s or -svalue
      if (shortName != null) {
        if (args[i] == '-$shortName') {
          if (i + 1 < args.length && !args[i + 1].startsWith('-')) {
            return args[i + 1];
          }
          // -s without value, use prompt if provided
          return prompt?.call();
        } else if (args[i].startsWith('-$shortName') && args[i].length > 2) {
          return args[i].substring(2);
        }
      }
    }

    // Not found in args, use prompt if provided
    return prompt?.call();
  }

  /// Parse a generic flag from arguments.
  /// Returns true if flag is present, false otherwise.
  /// Supports: --flag, -f
  bool parseFlag(List<String>? args, {required String longName, String? shortName}) {
    if (args == null || args.isEmpty) {
      return false;
    }

    for (final arg in args) {
      if (arg == '--$longName' || (shortName != null && arg == '-$shortName')) {
        return true;
      }
    }
    return false;
  }
}
