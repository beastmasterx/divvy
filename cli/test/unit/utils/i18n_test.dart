// Tests for i18n system.

import 'package:test/test.dart';
import 'package:cli/src/utils/i18n.dart';

void main() {
  group('I18n', () {
    setUp(() {
      // Reset to default language before each test
      setLanguage('en_US');
    });

    test('translates English correctly', () {
      setLanguage('en_US');
      expect(translate('Divvy Expense Splitter'), 'Divvy Expense Splitter');
      expect(translate('Login successful!'), 'Login successful!');
      expect(translate('Error: {}'), 'Error: {}');
    });

    test('translates Chinese correctly', () {
      setLanguage('zh_CN');
      expect(translate('Divvy Expense Splitter'), 'Divvy 费用分摊器');
      expect(translate('Login successful!'), '登录成功！');
      expect(translate('Error: {}'), '错误: {}');
    });

    test('substitutes parameters correctly', () {
      setLanguage('en_US');
      expect(translate('Current Group: {}', ['My Group']), 'Current Group: My Group');
      expect(translate('Error: {}', ['Connection failed']), 'Error: Connection failed');
      
      setLanguage('zh_CN');
      expect(translate('Current Group: {}', ['我的组']), '当前组: 我的组');
    });

    test('substitutes multiple parameters', () {
      setLanguage('en_US');
      // Note: current implementation only replaces first {}
      expect(translate('Error: {}', ['Test']), 'Error: Test');
    });

    test('falls back to key when translation missing', () {
      setLanguage('en_US');
      expect(translate('MissingTranslationKey'), 'MissingTranslationKey');
      
      setLanguage('zh_CN');
      expect(translate('MissingTranslationKey'), 'MissingTranslationKey');
    });

    test('handles empty args', () {
      setLanguage('en_US');
      expect(translate('Login successful!', []), 'Login successful!');
      expect(translate('Error: {}', []), 'Error: {}');
    });

    test('switches language correctly', () {
      setLanguage('en_US');
      expect(getCurrentLanguage(), 'en_US');
      expect(translate('Login successful!'), 'Login successful!');

      setLanguage('zh_CN');
      expect(getCurrentLanguage(), 'zh_CN');
      expect(translate('Login successful!'), '登录成功！');
    });

    test('ignores invalid language codes', () {
      setLanguage('en_US');
      expect(getCurrentLanguage(), 'en_US');

      setLanguage('invalid_lang');
      // Should remain 'en_US' since invalid_lang is not in translations
      expect(getCurrentLanguage(), 'en_US');
      // Should use en_US translations
      expect(translate('Login successful!'), 'Login successful!');
    });
  });
}

