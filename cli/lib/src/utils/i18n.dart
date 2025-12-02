// Internationalization utilities for translations.
//
// Supports en_US and zh_CN languages.

/// Current language (default: 'en_US').
String _currentLanguage = 'en_US';

/// Translation maps for supported languages.
final Map<String, Map<String, String>> _translations = {
  'en_US': {
    // Menu
    'Divvy Expense Splitter': 'Divvy Expense Splitter',
    'Current Group: {}': 'Current Group: {}',
    'Current Period: {}': 'Current Period: {}',
    '1. Login': '1. Login',
    '2. Register': '2. Register',
    '3. Logout': '3. Logout',
    '4. Select Group': '4. Select Group',
    '5. Create Group': '5. Create Group',
    '6. View Period': '6. View Period',
    '7. Create Period': '7. Create Period',
    '8. Add Transaction': '8. Add Transaction',
    '9. View Transactions': '9. View Transactions',
    '10. View Balances': '10. View Balances',
    '11. View Settlement Plan': '11. View Settlement Plan',
    '12. Apply Settlement': '12. Apply Settlement',
    '13. Settings': '13. Settings',
    '14. Exit': '14. Exit',
    'Enter your choice: ': 'Enter your choice: ',
    'Invalid choice, please try again.': 'Invalid choice, please try again.',
    'Exiting Divvy. Goodbye!': 'Exiting Divvy. Goodbye!',

    // Authentication
    'Email: ': 'Email: ',
    'Password: ': 'Password: ',
    'Name: ': 'Name: ',
    'Login successful!': 'Login successful!',
    'Registration successful!': 'Registration successful!',
    'Logged out successfully.': 'Logged out successfully.',
    'Invalid credentials.': 'Invalid credentials.',
    'Email already exists.': 'Email already exists.',

    // Groups
    'Group Name: ': 'Group Name: ',
    'Group created successfully.': 'Group created successfully.',
    'No groups available.': 'No groups available.',
    'Select a group:': 'Select a group:',
    'Group selected: {}': 'Group selected: {}',

    // Periods
    'Period Name: ': 'Period Name: ',
    'Period created successfully.': 'Period created successfully.',
    'No periods available.': 'No periods available.',
    'Select a period:': 'Select a period:',
    'Period closed successfully.': 'Period closed successfully.',

    // Transactions
    'Description (optional): ': 'Description (optional): ',
    'Amount: ': 'Amount: ',
    'Transaction created successfully.': 'Transaction created successfully.',
    'No transactions available.': 'No transactions available.',

    // Settlement
    'Settlement plan applied successfully.': 'Settlement plan applied successfully.',
    'No settlement needed.': 'No settlement needed.',

    // Errors
    'Error: {}': 'Error: {}',
    'Connection error. Please check your API URL.': 'Connection error. Please check your API URL.',
    'Unauthorized. Please login.': 'Unauthorized. Please login.',
    'Not found.': 'Not found.',
    'Validation error: {}': 'Validation error: {}',

    // Common
    'Yes': 'Yes',
    'No': 'No',
    'Cancel': 'Cancel',
    'Confirm': 'Confirm',
    'Success': 'Success',
    'Failed': 'Failed',
    'More Options': 'More Options',
    'More...': 'More...',
    'Back': 'Back',
  },
  'zh_CN': {
    // Menu
    'Divvy Expense Splitter': 'Divvy 费用分摊器',
    'Current Group: {}': '当前组: {}',
    'Current Period: {}': '当前周期: {}',
    '1. Login': '1. 登录',
    '2. Register': '2. 注册',
    '3. Logout': '3. 登出',
    '4. Select Group': '4. 选择组',
    '5. Create Group': '5. 创建组',
    '6. View Period': '6. 查看周期',
    '7. Create Period': '7. 创建周期',
    '8. Add Transaction': '8. 添加交易',
    '9. View Transactions': '9. 查看交易',
    '10. View Balances': '10. 查看余额',
    '11. View Settlement Plan': '11. 查看结算计划',
    '12. Apply Settlement': '12. 应用结算',
    '13. Settings': '13. 设置',
    '14. Exit': '14. 退出',
    'Enter your choice: ': '请输入选择: ',
    'Invalid choice, please try again.': '无效选择，请重试。',
    'Exiting Divvy. Goodbye!': '退出 Divvy。再见！',

    // Authentication
    'Email: ': '邮箱: ',
    'Password: ': '密码: ',
    'Name: ': '姓名: ',
    'Login successful!': '登录成功！',
    'Registration successful!': '注册成功！',
    'Logged out successfully.': '登出成功。',
    'Invalid credentials.': '无效的凭据。',
    'Email already exists.': '邮箱已存在。',

    // Groups
    'Group Name: ': '组名称: ',
    'Group created successfully.': '组创建成功。',
    'No groups available.': '没有可用的组。',
    'Select a group:': '选择一个组:',
    'Group selected: {}': '已选择组: {}',

    // Periods
    'Period Name: ': '周期名称: ',
    'Period created successfully.': '周期创建成功。',
    'No periods available.': '没有可用的周期。',
    'Select a period:': '选择一个周期:',
    'Period closed successfully.': '周期关闭成功。',

    // Transactions
    'Description (optional): ': '描述（可选）: ',
    'Amount: ': '金额: ',
    'Transaction created successfully.': '交易创建成功。',
    'No transactions available.': '没有可用的交易。',

    // Settlement
    'Settlement plan applied successfully.': '结算计划应用成功。',
    'No settlement needed.': '无需结算。',

    // Errors
    'Error: {}': '错误: {}',
    'Connection error. Please check your API URL.': '连接错误。请检查您的 API URL。',
    'Unauthorized. Please login.': '未授权。请登录。',
    'Not found.': '未找到。',
    'Validation error: {}': '验证错误: {}',

    // Common
    'Yes': '是',
    'No': '否',
    'Cancel': '取消',
    'Confirm': '确认',
    'Success': '成功',
    'Failed': '失败',
    'More Options': '更多选项',
    'More...': '更多...',
    'Back': '返回',
  },
};

/// Get translation for a key, with optional format arguments.
///
/// Parameters:
/// - [key]: The translation key
/// - [args]: Optional arguments for string formatting (using {})
///
/// Returns:
/// The translated string with arguments substituted
String translate(String key, [List<Object>? args]) {
  final langTranslations = _translations[_currentLanguage] ?? _translations['en_US']!;
  final translation = langTranslations[key] ?? key;

  if (args == null || args.isEmpty) {
    return translation;
  }

  // Simple {} replacement
  String result = translation;
  for (final arg in args) {
    result = result.replaceFirst('{}', arg.toString());
  }
  return result;
}

// Alias for translate() - matches Python's _() function.
// ignore: unused_element
String _(String key, [List<Object>? args]) => translate(key, args);

/// Set the current language.
///
/// Parameters:
/// - [lang]: Language code ('en_US' or 'zh_CN')
void setLanguage(String lang) {
  if (_translations.containsKey(lang)) {
    _currentLanguage = lang;
  }
}

/// Get the current language.
String getCurrentLanguage() => _currentLanguage;

/// Initialize i18n from preferences.
///
/// Parameters:
/// - [language]: Language code from preferences
Future<void> initialize(String language) async {
  setLanguage(language);
}

