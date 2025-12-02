// Service layer for category operations.

import 'package:divvy_api_client/divvy_api_client.dart';

import '../api/client.dart';

/// Category service for managing categories.
class CategoryService {
  final DivvyClient _client;

  CategoryService(this._client);

  /// List all categories.
  Future<List<CategoryResponse>> listCategories() async {
    try {
      final response = await _client.categories.getAllCategoriesApiV1CategoriesGet();
      return response.data?.toList() ?? [];
    } catch (e) {
      return [];
    }
  }
}
