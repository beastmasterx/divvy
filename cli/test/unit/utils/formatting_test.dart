import 'package:test/test.dart';
import 'package:cli/src/utils/formatting.dart';

void main() {
  group('getDisplayWidth', () {
    test('ASCII characters count as 1', () {
      expect(getDisplayWidth('abc'), 3);
      expect(getDisplayWidth('Hello World'), 11);
      expect(getDisplayWidth('123'), 3);
    });

    test('CJK characters count as 2', () {
      // Chinese characters
      expect(getDisplayWidth('你好'), 4);
      expect(getDisplayWidth('测试'), 4);
      
      // Japanese characters
      expect(getDisplayWidth('テスト'), 6);
    });

    test('Mixed ASCII and CJK', () {
      expect(getDisplayWidth('Hello 世界'), 10); // 5 + 1 + 4
      expect(getDisplayWidth('Test 测试'), 9); // 4 + 1 + 4
    });

    test('Empty string', () {
      expect(getDisplayWidth(''), 0);
    });

    test('Numbers and symbols', () {
      expect(getDisplayWidth('123.45'), 6);
      expect(getDisplayWidth(r'$100'), 4);
    });
  });

  group('padToDisplayWidth', () {
    test('left align (default)', () {
      expect(padToDisplayWidth('abc', 10, '<'), 'abc       ');
      expect(padToDisplayWidth('test', 8, '<'), 'test    ');
    });

    test('right align', () {
      expect(padToDisplayWidth('abc', 10, '>'), '       abc');
      expect(padToDisplayWidth('test', 8, '>'), '    test');
    });

    test('center align', () {
      expect(padToDisplayWidth('abc', 10, '^'), '   abc    ');
      expect(padToDisplayWidth('test', 9, '^'), '  test   ');
    });

    test('no padding needed', () {
      expect(padToDisplayWidth('abc', 3, '<'), 'abc');
      expect(padToDisplayWidth('test', 2, '<'), 'test'); // Longer than target
    });

    test('CJK characters padding', () {
      expect(padToDisplayWidth('你好', 10, '<'), '你好      '); // 4 display width + 6 spaces = 10
      expect(padToDisplayWidth('测试', 8, '>'), '    测试'); // 4 display width + 4 spaces = 8
    });
  });

  group('centsToDollars', () {
    test('converts cents to dollars', () {
      expect(centsToDollars(12345), '123.45');
      expect(centsToDollars(100), '1.00');
      expect(centsToDollars(1), '0.01');
      expect(centsToDollars(0), '0.00');
    });

    test('handles negative amounts', () {
      expect(centsToDollars(-12345), '123.45'); // abs() is used
      expect(centsToDollars(-100), '1.00');
    });
  });

  group('formatAmountWithSign', () {
    test('positive amounts', () {
      expect(formatAmountWithSign(12345), r'+$123.45');
      expect(formatAmountWithSign(100), r'+$1.00');
      expect(formatAmountWithSign(0), r'+$0.00');
    });

    test('negative amounts', () {
      expect(formatAmountWithSign(-12345), r'-$123.45');
      expect(formatAmountWithSign(-100), r'-$1.00');
    });
  });
}

