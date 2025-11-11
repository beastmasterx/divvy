// Openapi Generator last run: : 2025-11-11T23:18:33.334643
import 'package:openapi_generator_annotations/openapi_generator_annotations.dart';

/// Run `dart run build_runner build --delete-conflicting-outputs` to generate the API client.
@Openapi(
  additionalProperties: AdditionalProperties(
    pubName: 'divvy_api_client',
    pubDescription: 'Divvy API Client',
  ),
  inputSpec: InputSpec(path: 'api/openapi.json'),
  outputDirectory: 'lib/src/generated/api/divvy',
  generatorName: Generator.dio,
)
class DivvyApiGenerator {}