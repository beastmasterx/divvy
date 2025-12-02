// Service layer for group operations.

import 'package:divvy_api_client/divvy_api_client.dart';

import '../api/client.dart';

/// Group service for managing groups.
class GroupService {
  final DivvyClient _client;

  GroupService(this._client);

  /// List all groups for the current user.
  Future<List<GroupResponse>> listGroups() async {
    final response = await _client.groups.getGroupsByUserIdApiV1GroupsGet();
    return response.data?.toList() ?? [];
  }

  /// Get a group by ID.
  Future<GroupResponse?> getGroup(int groupId) async {
    try {
      final response = await _client.groups.getGroupByIdApiV1GroupsGroupIdGet(groupId: groupId);
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Create a new group.
  Future<GroupResponse?> createGroup(String name) async {
    try {
      final request = GroupRequest((b) => b..name = name);
      final response = await _client.groups.createGroupApiV1GroupsPost(groupRequest: request);
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Update a group.
  Future<GroupResponse?> updateGroup(int groupId, String name) async {
    try {
      final request = GroupRequest((b) => b..name = name);
      final response = await _client.groups.updateGroupApiV1GroupsGroupIdPut(groupId: groupId, groupRequest: request);
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Delete a group.
  Future<bool> deleteGroup(int groupId) async {
    try {
      await _client.groups.deleteGroupApiV1GroupsGroupIdDelete(groupId: groupId);
      return true;
    } catch (e) {
      return false;
    }
  }

  /// Get the current active period for a group.
  Future<PeriodResponse?> getCurrentPeriod(int groupId) async {
    try {
      final response = await _client.groups.getCurrentPeriodApiV1GroupsGroupIdPeriodsCurrentGet(
        groupId: groupId,
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }
}
