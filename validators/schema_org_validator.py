from .base_validator import BaseValidator
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaOrgValidator(BaseValidator):
    SCHEMA_VALIDATOR_ENDPOINT = "https://validator.schema.org/validate"

    def __init__(self):
        super().__init__()

    def validate_with_schema_org(self, url: str) -> dict:
        """Validate schema using official Schema.org validator with improved error handling"""
        try:
            response = requests.post(self.SCHEMA_VALIDATOR_ENDPOINT, data={"url": url}, timeout=30)
            response.raise_for_status()

            # Handle Schema.org validator's specific response format
            response_text = response.text
            if response_text.startswith(")]}'"):
                response_text = response_text[5:]

            try:
                data = json.loads(response_text)
                return self.process_schema_org_response(data)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from Schema.org validator: {str(e)}")
                return {
                    'is_valid': False,
                    'errors': ["Invalid response format from Schema.org validator"],
                    'warnings': []
                }
        except requests.Timeout:
            logger.error("Schema.org validation request timed out")
            return {
                'is_valid': False,
                'errors': ["Schema.org validation request timed out"],
                'warnings': []
            }
        except requests.RequestException as e:
            logger.error(f"Error validating with Schema.org: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Schema.org validation error: {str(e)}"],
                'warnings': []
            }

    def process_schema_org_response(self, data: dict) -> dict:
        """Process and structure Schema.org validator response with enhanced error handling"""
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'schema_data': {}
        }

        try:
            # Process triple groups
            triple_groups = data.get('tripleGroups', [])
            if not triple_groups:
                logger.warning("No triple groups found in Schema.org response")
                validation_results['warnings'].append("No schema data found in the response")
                return validation_results

            for triple_group in triple_groups:
                # Process nodes in each triple group
                nodes = triple_group.get('nodes', [])
                for node in nodes:
                    # Extract node type information
                    node_type = node.get('type', 'Unknown')
                    
                    # Process properties
                    for prop in node.get('properties', []):
                        pred = prop.get('pred')
                        value = prop.get('value')
                        
                        if prop.get('errors'):
                            validation_results['is_valid'] = False
                            for error in prop['errors']:
                                error_msg = f"{node_type} - {pred}: {error}"
                                validation_results['errors'].append(error_msg)
                        
                        elif prop.get('warnings'):
                            for warning in prop['warnings']:
                                warning_msg = f"{node_type} - {pred}: {warning}"
                                validation_results['warnings'].append(warning_msg)
                        
                        elif pred and value:
                            if node_type not in validation_results['schema_data']:
                                validation_results['schema_data'][node_type] = {}
                            validation_results['schema_data'][node_type][pred] = value

            return validation_results
            
        except Exception as e:
            logger.error(f"Error processing Schema.org response: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Error processing validation response: {str(e)}"],
                'warnings': []
            }
