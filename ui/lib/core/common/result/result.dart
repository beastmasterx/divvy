/// A sealed class representing the result of an operation that can either succeed or fail.
///
/// This provides a type-safe way to handle success and error cases without throwing exceptions.
/// Use pattern matching (switch expressions/statements) to handle both cases exhaustively.
///
/// Example:
/// ```dart
/// Result<int> divide(int a, int b) {
///   if (b == 0) return Result.error('Cannot divide by zero');
///   return Result.ok(a ~/ b);
/// }
///
/// final result = divide(10, 2);
/// switch (result) {
///   case Ok(:final value):
///     print('Result: $value');
///   case Error(:final error):
///     print('Error: $error');
/// }
/// ```
sealed class Result<T> {
  const Result();

  /// Creates a successful result containing the given [value].
  factory Result.ok(T value) = Ok<T>;

  /// Creates an error result containing the given [error].
  factory Result.error(T error) = Error<T>;
}

/// Represents a successful result containing a [value].
class Ok<T> extends Result<T> {
  const Ok(this.value);

  /// The successful value returned from the operation.
  final T value;
}

/// Represents a failed result containing an [error].
class Error<T> extends Result<T> {
  const Error(this.error);

  /// The error that occurred during the operation.
  final T error;
}
