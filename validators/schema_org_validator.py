from typing import Dict, Any
import requests
import json
import logging
from .base_validator import BaseValidator

logger = logging.getLogger(__name__)

class SchemaOrgValidator(BaseValidator):
    """Handles Schema.org specific validation logic."""
    
    SCHEMA_VALIDATOR_ENDPOINT = "https://validator.schema.org/validate"

    def __init__(self, schema_types_df=None):
        """Initialize Schema.org validator with proper headers."""
        super().__init__(schema_types_df)
        self.headers = {
            'User-Agent': 'Schema Analysis Tool/1.0',
            'Accept': 'application/json'
        }

    def validate_url(self, url: str) -> Dict[str, Any]:
        """
        Validate a URL using the Schema.org validator.
        
        Args:
            url: The URL to validate
            
        Returns:
            Dict containing validation results
        """
        try:
            response = requests.post(
                self.SCHEMA_VALIDATOR_ENDPOINT,
                data={"url": url},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()

            return self._process_validator_response(response.text)
        except requests.Timeout:
            logger.error("Schema.org validator request timed out")
            raise Exception("Schema.org validator request timed out. Please try again.")
        except requests.RequestException as e:
            logger.error(f"Error accessing Schema.org validator: {str(e)}")
            raise Exception(f"Error accessing Schema.org validator: {str(e)}")

    def validate_schema(self, schema_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema data directly using Schema.org validator.
        
        Args:
            schema_data: The schema data to validate
            
        Returns:
            Dict containing validation results
        """
        try:
            if not isinstance(schema_data, dict):
                raise ValueError("Schema data must be a dictionary")

            if '@context' not in schema_data:
                raise ValueError("Schema data must include @context")

            validation_data = self.validate_url(schema_data['@context'])
            return self._extract_validation_details(validation_data)
        except Exception as e:
            logger.error(f"Schema validation error: {str(e)}")
            raise

    def _process_validator_response(self, response_text: str) -> Dict[str, Any]:
        """Process and parse Schema.org validator response."""
        try:
            # Handle Schema.org's specific response format
            if response_text.startswith(")]}'\n"):
                response_text = response_text[5:]

            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Schema.org validator: {str(e)}")
            raise Exception(f"Invalid response format from Schema.org validator: {str(e)}")

    def _extract_validation_details(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract detailed validation information from validator response."""
        validation_details = {
            'errors': [],
            'warnings': [],
            'schema_data': {},
            'validation_details': {
                'num_triples': 0,
                'num_nodes': 0,
                'properties_found': set()
            }
        }

        try:
            for triple_group in data.get('tripleGroups', []):
                validation_details['validation_details']['num_triples'] += 1
                
                for node in triple_group.get('nodes', []):
                    validation_details['validation_details']['num_nodes'] += 1
                    node_type = node.get('type', 'Unknown')
                    
                    for prop in node.get('properties', []):
                        prop_name = prop.get('pred', '')
                        validation_details['validation_details']['properties_found'].add(prop_name)
                        
                        if prop.get('errors'):
                            for error in prop['errors']:
                                validation_details['errors'].append({
                                    'property': prop_name,
                                    'message': error,
                                    'node_type': node_type
                                })
                        elif prop.get('warnings'):
                            for warning in prop['warnings']:
                                validation_details['warnings'].append({
                                    'property': prop_name,
                                    'message': warning,
                                    'node_type': node_type
                                })
                        else:
                            validation_details['schema_data'][prop_name] = {
                                'value': prop['value'],
                                'node_type': node_type
                            }

            # Convert properties_found set to list for JSON serialization
            validation_details['validation_details']['properties_found'] = list(
                validation_details['validation_details']['properties_found']
            )
            
            return validation_details
        except Exception as e:
            logger.error(f"Error extracting validation details: {str(e)}")
            raise Exception(f"Error processing validation details: {str(e)}")
