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
        """Validate schema using official Schema.org validator"""
        try:
            response = requests.post(self.SCHEMA_VALIDATOR_ENDPOINT, data={"url": url})
            response.raise_for_status()

            # Handle Schema.org validator's specific response format
            if response.text.startswith(")]}'"):
                response_text = response.text[5:]
            else:
                response_text = response.text

            data = json.loads(response_text)
            return self.process_schema_org_response(data)
        except requests.RequestException as e:
            logger.error(f"Error validating with Schema.org: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Schema.org validation error: {str(e)}"],
                'warnings': []
            }

    def process_schema_org_response(self, data: dict) -> dict:
        """Process and structure Schema.org validator response"""
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'schema_data': {}
        }

        try:
            for triple_group in data.get('tripleGroups', []):
                for node in triple_group.get('nodes', []):
                    for prop in node.get('properties', []):
                        if prop.get('errors'):
                            validation_results['is_valid'] = False
                            validation_results['errors'].extend(prop['errors'])
                        elif prop.get('warnings'):
                            validation_results['warnings'].extend(prop['warnings'])
                        else:
                            validation_results['schema_data'][prop['pred']] = prop['value']

            return validation_results
        except Exception as e:
            logger.error(f"Error processing Schema.org response: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Error processing validation response: {str(e)}"],
                'warnings': []
            }
