from .base_validator import BaseValidator
import json

class JSONValidator(BaseValidator):
    def validate_json_ld(self, schema_data: Dict) -> Dict[str, Any]:
        try:
            validation_results = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }
            
            if not isinstance(schema_data, dict):
                validation_results['is_valid'] = False
                validation_results['errors'].append(
                    f"Invalid schema data type: expected dict, got {type(schema_data)}"
                )
                return validation_results
            
            try:
                json.dumps(schema_data)
            except Exception as e:
                validation_results['is_valid'] = False
                validation_results['errors'].append(f"Invalid JSON structure: {str(e)}")
                return validation_results
            
            required_props = ['@context', '@type']
            for prop in required_props:
                if prop not in schema_data:
                    validation_results['errors'].append(f"Missing required property: {prop}")
                    validation_results['is_valid'] = False
            
            if '@context' in schema_data:
                context = schema_data['@context']
                if context not in ['https://schema.org', 'http://schema.org']:
                    validation_results['warnings'].append(
                        f"Non-standard @context value: {context}. Recommended: 'https://schema.org'"
                    )
                elif context == 'http://schema.org':
                    validation_results['warnings'].append(
                        "Using 'http://schema.org'. Recommended: 'https://schema.org'"
                    )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"JSON-LD validation error: {type(e).__name__} - {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {type(e).__name__} - {str(e)}"],
                'warnings': []
            }
