/// Service layer for member operations.

import 'package:divvy_api_client/src/model/member_response.dart';
import 'package:divvy_api_client/src/model/member_create.dart';
import 'package:built_collection/built_collection.dart';
import '../api/divvy_client.dart';

/// Member data structure
class Member {
  final int id;
  final String email;
  final String name;
  final bool isActive;
  final bool paidRemainderInCycle;

  Member({
    required this.id,
    required this.email,
    required this.name,
    required this.isActive,
    required this.paidRemainderInCycle,
  });
}

/// List all members.
/// 
/// Parameters:
/// - [client]: The API client
/// - [activeOnly]: If true, only return active members
/// 
/// Returns:
/// List of members
Future<List<Member>> listMembers(
  DivvyClient client, {
  bool activeOnly = false,
}) async {
  final response = await client.members.listMembersApiV1MembersGet(
    activeOnly: activeOnly,
  );
  final members = response.data ?? BuiltList<MemberResponse>();
  return members.map((m) => Member(
    id: m.id,
    email: m.email,
    name: m.name,
    isActive: m.isActive,
    paidRemainderInCycle: m.paidRemainderInCycle,
  )).toList();
}

/// Create a new member.
/// 
/// Parameters:
/// - [client]: The API client
/// - [email]: Member email
/// - [name]: Member name
/// 
/// Returns:
/// Success or error message
Future<String> createMember(
  DivvyClient client,
  String email,
  String name,
) async {
  final request = MemberCreate((b) => b
    ..email = email
    ..name = name);
  final response = await client.members.createMemberApiV1MembersPost(
    memberCreate: request,
  );
  return response.data?.message ?? 'Success';
}

/// Remove (deactivate) a member.
/// 
/// Parameters:
/// - [client]: The API client
/// - [memberId]: Member ID
/// 
/// Returns:
/// Success or error message
Future<String> removeMember(
  DivvyClient client,
  int memberId,
) async {
  final response = await client.members.removeMemberApiV1MembersMemberIdDelete(
    memberId: memberId,
  );
  return response.data?.message ?? 'Success';
}

/// Rejoin (reactivate) an inactive member.
/// 
/// Parameters:
/// - [client]: The API client
/// - [memberId]: Member ID
/// 
/// Returns:
/// Success or error message
Future<String> rejoinMember(
  DivvyClient client,
  int memberId,
) async {
  final response = await client.members.rejoinMemberApiV1MembersMemberIdRejoinPost(
    memberId: memberId,
  );
  return response.data?.message ?? 'Success';
}

/// Get member by email.
/// 
/// Parameters:
/// - [client]: The API client
/// - [email]: Member email
/// 
/// Returns:
/// Member if found, null otherwise
Future<Member?> getMemberByEmail(
  DivvyClient client,
  String email,
) async {
  // Get all members and find by email
  final members = await listMembers(client, activeOnly: false);
  try {
    return members.firstWhere((m) => m.email == email);
  } catch (e) {
    return null;
  }
}

/// Get member by name.
/// 
/// Parameters:
/// - [client]: The API client
/// - [name]: Member name
/// 
/// Returns:
/// Member if found, null otherwise
Future<Member?> getMemberByName(
  DivvyClient client,
  String name,
) async {
  // Get all members and find by name
  final members = await listMembers(client, activeOnly: false);
  try {
    return members.firstWhere((m) => m.name == name);
  } catch (e) {
    return null;
  }
}

