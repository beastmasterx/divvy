// Service layer for user operations.

import 'package:divvy_api_client/divvy_api_client.dart';

import '../api/client.dart';

/// User service for managing user profile.
class UserService {
  final DivvyClient _client;

  UserService(this._client);

  /// Get current user information.
  Future<UserResponse?> getCurrentUser() async {
    try {
      final response =
          await _client.user.getCurrentUserInfoApiV1UserMeGet();
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Update user profile.
  Future<UserResponse?> updateProfile({
    String? email,
    String? name,
    bool? isActive,
    String? avatar,
  }) async {
    try {
      final request = ProfileRequest((b) {
        if (email != null) b.email = email;
        if (name != null) b.name = name;
        if (isActive != null) b.isActive = isActive;
        if (avatar != null) b.avatar = avatar;
      });

      final response = await _client.user.updateUserProfileApiV1UserMePut(
        profileRequest: request,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }
}

