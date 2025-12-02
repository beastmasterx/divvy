// Error handling utilities.

import 'package:dio/dio.dart';

import 'i18n.dart';

/// Handle and format API errors.
String formatApiError(dynamic error) {
  if (error is DioException) {
    return _formatDioError(error);
  }
  return translate('Error: {}', [error.toString()]);
}

/// Format DioException errors.
String _formatDioError(DioException error) {
  switch (error.type) {
    case DioExceptionType.connectionTimeout:
    case DioExceptionType.sendTimeout:
    case DioExceptionType.receiveTimeout:
      return translate('Connection error. Please check your API URL.');
    case DioExceptionType.badResponse:
      final statusCode = error.response?.statusCode;
      if (statusCode == 401) {
        return translate('Unauthorized. Please login.');
      } else if (statusCode == 403) {
        return translate('Forbidden. You do not have permission.');
      } else if (statusCode == 404) {
        return translate('Not found.');
      } else if (statusCode == 409) {
        return translate('Conflict. Resource already exists.');
      } else if (statusCode == 422) {
        final message = _extractValidationError(error);
        return translate('Validation error: {}', [message]);
      } else if (statusCode != null && statusCode >= 500) {
        return translate('Server error. Please try again later.');
      } else {
        return translate('Error: {}', ['HTTP $statusCode']);
      }
    case DioExceptionType.cancel:
      return translate('Request cancelled.');
    case DioExceptionType.connectionError:
      return translate('Connection error. Please check your API URL.');
    case DioExceptionType.badCertificate:
      return translate('SSL certificate error.');
    case DioExceptionType.unknown:
      final message = error.message ?? error.toString();
      return translate('Error: {}', [message]);
  }
}

/// Extract validation error message from response.
String _extractValidationError(DioException error) {
  try {
    final data = error.response?.data;
    if (data is Map<String, dynamic>) {
      final detail = data['detail'];
      if (detail is List && detail.isNotEmpty) {
        final firstError = detail[0];
        if (firstError is Map<String, dynamic>) {
          return firstError['msg'] as String? ?? 'Invalid input';
        }
      }
      return data['message'] as String? ?? 'Invalid input';
    }
  } catch (e) {
    // Ignore parsing errors
  }
  return 'Invalid input';
}

/// Check if error is a network error.
bool isNetworkError(dynamic error) {
  if (error is DioException) {
    return error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.sendTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.connectionError;
  }
  return false;
}

/// Check if error is an authentication error.
bool isAuthError(dynamic error) {
  if (error is DioException) {
    return error.response?.statusCode == 401;
  }
  return false;
}

