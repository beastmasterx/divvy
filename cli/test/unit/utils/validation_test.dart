import 'package:test/test.dart';
import 'package:cli/src/utils/validation.dart';

void main() {
  group('validateAmount', () {
    test('valid dollar amounts', () {
      final result1 = validateAmount('123.45');
      expect(result1.isValid, true);
      expect(result1.amountInCents, 12345);
      expect(result1.errorMessage, '');

      final result2 = validateAmount('100');
      expect(result2.isValid, true);
      expect(result2.amountInCents, 10000);

      final result3 = validateAmount('0.01');
      expect(result3.isValid, true);
      expect(result3.amountInCents, 1);

      final result4 = validateAmount(r'$123.45');
      expect(result4.isValid, true);
      expect(result4.amountInCents, 12345);
    });

    test('rounds to nearest cent', () {
      final result1 = validateAmount('123.456');
      expect(result1.isValid, true);
      expect(result1.amountInCents, 12346); // Rounds up

      final result2 = validateAmount('123.454');
      expect(result2.isValid, true);
      expect(result2.amountInCents, 12345); // Rounds down
    });

    test('invalid amounts', () {
      final result1 = validateAmount('');
      expect(result1.isValid, false);
      expect(result1.amountInCents, 0);
      expect(result1.errorMessage, contains('empty'));

      final result2 = validateAmount('abc');
      expect(result2.isValid, false);
      expect(result2.errorMessage, contains('Invalid'));

      final result3 = validateAmount('0');
      expect(result3.isValid, false);
      expect(result3.errorMessage, contains('greater than zero'));

      final result4 = validateAmount('-10');
      expect(result4.isValid, false);
      expect(result4.errorMessage, contains('greater than zero'));
    });

    test('handles whitespace', () {
      final result1 = validateAmount('  123.45  ');
      expect(result1.isValid, true);
      expect(result1.amountInCents, 12345);
    });
  });

  group('validateEmail', () {
    test('valid emails', () {
      expect(validateEmail('test@example.com'), true);
      expect(validateEmail('user.name@domain.co.uk'), true);
      expect(validateEmail('alice+tag@example.org'), true);
    });

    test('invalid emails', () {
      expect(validateEmail(''), false);
      expect(validateEmail('invalid'), false);
      expect(validateEmail('@example.com'), false);
      expect(validateEmail('test@'), false);
      expect(validateEmail('test.example.com'), false);
    });

    test('handles whitespace', () {
      expect(validateEmail('  test@example.com  '), true);
    });
  });

  group('validateName', () {
    test('valid names', () {
      final result1 = validateName('Alice');
      expect(result1.isValid, true);
      expect(result1.errorMessage, '');

      final result2 = validateName('Bob Smith');
      expect(result2.isValid, true);

      final result3 = validateName('A');
      expect(result3.isValid, true);
    });

    test('invalid names', () {
      final result1 = validateName('');
      expect(result1.isValid, false);
      expect(result1.errorMessage, contains('empty'));

      final result2 = validateName('   ');
      expect(result2.isValid, false);
      expect(result2.errorMessage, contains('empty'));
    });
  });

  group('validatePeriodName', () {
    test('always valid (optional field)', () {
      expect(validatePeriodName(''), true);
      expect(validatePeriodName('Period 1'), true);
      expect(validatePeriodName('Any name'), true);
    });
  });
}

