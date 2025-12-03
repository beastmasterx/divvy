// Service layer for category operations.

import '../api/client.dart';
import '../api/schemas.dart';

/// Category service for managing categories.
class CategoryService {
  final Client _client;

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
