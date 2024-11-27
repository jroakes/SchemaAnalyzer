from typing import Dict, List, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)

class BaseValidator:
    def __init__(self, schema_types_df=None):
        self.schema_types_df = schema_types_df

    def validate_schema_structure(self, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate basic schema structure and required fields.
        
        Args:
            schema_data: The schema data to validate
            
        Returns:
            Dict containing validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }

        if not isinstance(schema_data, dict):
            validation_result['is_valid'] = False
            validation_result['errors'].append("Schema data must be a dictionary")
            return validation_result

        # Check required properties
        required_props = ['@context', '@type']
        for prop in required_props:
            if prop not in schema_data:
                validation_result['is_valid'] = False
                validation_result['errors'].append(f"Missing required property: {prop}")

        # Validate @context
        if '@context' in schema_data:
            context = schema_data['@context']
            if context not in ['https://schema.org', 'http://schema.org']:
                validation_result['warnings'].append(
                    f"Non-standard @context value: {context}. Recommended: 'https://schema.org'"
                )
            elif context == 'http://schema.org':
                validation_result['warnings'].append(
                    "Using 'http://schema.org'. Recommended: 'https://schema.org'"
                )

        return validation_result

    def get_schema_type_info(self, schema_type: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific schema type from the schema types DataFrame.
        
        Args:
            schema_type: The schema type to look up
            
        Returns:
            Dict containing schema type information or None if not found
        """
        if self.schema_types_df is None:
            return None

        schema_info = self.schema_types_df[self.schema_types_df['Name'] == schema_type]
        if schema_info.empty:
            return None

        return {
            'name': schema_type,
            'description': schema_info['Description'].iloc[0],
            'url': schema_info['Schema URL'].iloc[0],
            'google_url': schema_info['Google Doc URL'].iloc[0] if 'Google Doc URL' in schema_info else None
        }

    def format_validation_message(self, message_type: str, message: str, suggestion: Optional[str] = None) -> Dict[str, Any]:
        """
        Format validation messages consistently.
        
        Args:
            message_type: Type of message (error, warning, info)
            message: The main message
            suggestion: Optional suggestion for improvement
            
        Returns:
            Dict containing formatted message
        """
        return {
            'severity': message_type,
            'message': message,
            'suggestion': suggestion
        }
