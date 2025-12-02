// Tests for error handling utilities.

import 'package:dio/dio.dart';
import 'package:test/test.dart';
import 'package:cli/src/utils/errors.dart';
import 'package:cli/src/utils/i18n.dart';

void main() {
  setUp(() {
    // Set language for consistent test output
    setLanguage('en_US');
  });

  group('formatApiError', () {
    test('formats connection timeout errors', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.connectionTimeout,
      );
      final message = formatApiError(error);
      expect(message, contains('Connection error'));
    });

    test('formats 401 unauthorized errors', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 401,
        ),
      );
      final message = formatApiError(error);
      expect(message, contains('Unauthorized'));
    });

    test('formats 404 not found errors', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 404,
        ),
      );
      final message = formatApiError(error);
      expect(message, contains('Not found'));
    });

    test('formats 422 validation errors', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 422,
          data: {
            'detail': [
              {'msg': 'Invalid email format', 'type': 'value_error'}
            ]
          },
        ),
      );
      final message = formatApiError(error);
      expect(message, contains('Validation error'));
      expect(message, contains('Invalid email format'));
    });

    test('formats 500 server errors', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 500,
        ),
      );
      final message = formatApiError(error);
      expect(message, contains('Server error'));
    });

    test('formats connection errors', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.connectionError,
      );
      final message = formatApiError(error);
      expect(message, contains('Connection error'));
    });

    test('formats unknown errors', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.unknown,
        message: 'Custom error message',
      );
      final message = formatApiError(error);
      expect(message, contains('Custom error message'));
    });

    test('formats non-DioException errors', () {
      final error = Exception('Generic exception');
      final message = formatApiError(error);
      expect(message, contains('Error:'));
      expect(message, contains('Generic exception'));
    });
  });

  group('isNetworkError', () {
    test('returns true for connection timeout', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.connectionTimeout,
      );
      expect(isNetworkError(error), isTrue);
    });

    test('returns true for connection error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.connectionError,
      );
      expect(isNetworkError(error), isTrue);
    });

    test('returns false for 401 error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 401,
        ),
      );
      expect(isNetworkError(error), isFalse);
    });

    test('returns false for non-DioException', () {
      expect(isNetworkError(Exception('test')), isFalse);
    });
  });

  group('isAuthError', () {
    test('returns true for 401 error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 401,
        ),
      );
      expect(isAuthError(error), isTrue);
    });

    test('returns false for 404 error', () {
      final error = DioException(
        requestOptions: RequestOptions(path: '/test'),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: RequestOptions(path: '/test'),
          statusCode: 404,
        ),
      );
      expect(isAuthError(error), isFalse);
    });

    test('returns false for non-DioException', () {
      expect(isAuthError(Exception('test')), isFalse);
    });
  });
}

