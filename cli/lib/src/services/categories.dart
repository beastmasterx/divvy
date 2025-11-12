// Service layer for category operations.

import 'package:divvy_api_client/src/model/category_response.dart';
import 'package:built_collection/built_collection.dart';
import '../api/divvy_client.dart';

/// Category data structure
class Category {
  final int id;
  final String name;

  Category({required this.id, required this.name});
}

/// List all categories.
///
/// Parameters:
/// - [client]: The API client
///
/// Returns:
/// List of categories, ordered by name
Future<List<Category>> listCategories(DivvyClient client) async {
  final response = await client.categories.listCategoriesApiV1CategoriesGet();
  final categories = response.data ?? BuiltList<CategoryResponse>();
  return categories.map((c) => Category(id: c.id, name: c.name)).toList();
}
