import requests
from functools import lru_cache
import streamlit as st
from gpt_schema_analyzer import GPTSchemaAnalyzer
from competitor_analyzer import CompetitorAnalyzer
import logging
import json
import urllib.parse
from utils import clean_schema_type
from typing import Dict, Any, Optional, List, Union
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaOrgValidator:
    """Handles Schema.org specific validation logic."""
    
    SCHEMA_VALIDATOR_ENDPOINT = "https://validator.schema.org/validate"

    def __init__(self):
        """Initialize Schema.org validator with proper headers."""
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

class SchemaValidator:
    """Main schema validator class that coordinates different validation strategies."""

    def __init__(self, schema_types_df, keyword: Optional[str] = None):
        """
        Initialize SchemaValidator with necessary components.
        
        Args:
            schema_types_df: DataFrame containing schema type information
            keyword: Optional keyword for competitor analysis
        """
        self.schema_types_df = schema_types_df
        self.gpt_analyzer = GPTSchemaAnalyzer()
        self.schema_org_validator = SchemaOrgValidator()
        self.keyword = keyword

    def validate_schema(self, current_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema using multiple validation strategies.
        
        Args:
            current_schema: The schema data to validate
            
        Returns:
            Dict containing validation results
        """
        try:
            validation_results = {
                'good_schemas': [],
                'needs_improvement': [],
                'suggested_additions': [],
                'all_types': [],
                'errors': [],
                'warnings': []
            }

            if not current_schema:
                validation_results['warnings'].append({
                    'severity': 'warning',
                    'message': 'No schema data found on the page',
                    'suggestion': 'Consider implementing schema markup to improve search visibility'
                })
                
                competitor_recommendations = self._get_competitor_recommendations()
                if competitor_recommendations:
                    validation_results['suggested_additions'] = competitor_recommendations
                return validation_results

            # Process each schema type
            for schema_type, schema_data in current_schema.items():
                try:
                    validation_entry = {
                        'type': schema_type,
                        'data': schema_data,
                        'issues': []
                    }

                    # Validate using Schema.org validator
                    schema_validation = self.schema_org_validator.validate_schema(schema_data)
                    
                    if schema_validation['errors']:
                        validation_entry['issues'].extend([
                            {'severity': 'error', 'message': error['message']}
                            for error in schema_validation['errors']
                        ])
                        validation_results['needs_improvement'].append(validation_entry)
                    else:
                        if schema_validation['warnings']:
                            validation_entry['issues'].extend([
                                {'severity': 'warning', 'message': warning['message']}
                                for warning in schema_validation['warnings']
                            ])
                            validation_results['needs_improvement'].append(validation_entry)
                        else:
                            validation_results['good_schemas'].append(validation_entry)

                    validation_results['all_types'].append(schema_type)

                except Exception as e:
                    logger.error(f"Error validating schema {schema_type}: {str(e)}")
                    validation_results['errors'].append({
                        'severity': 'error',
                        'message': f'Validation error for {schema_type}: {str(e)}'
                    })

            # Add competitor-based recommendations
            competitor_suggestions = self._get_competitor_recommendations()
            if competitor_suggestions:
                current_types = set(schema_type for schema_type in current_schema.keys())
                for suggestion in competitor_suggestions:
                    if suggestion['type'] not in current_types:
                        validation_results['suggested_additions'].append(suggestion)

            return validation_results

        except Exception as e:
            logger.error(f"Error in schema validation: {str(e)}")
            return {
                'good_schemas': [],
                'needs_improvement': [],
                'suggested_additions': [],
                'errors': [{'message': f"Validation error: {str(e)}"}],
                'warnings': []
            }

    def _get_competitor_recommendations(self) -> List[Dict[str, Any]]:
        """Get schema recommendations based on competitor analysis."""
        try:
            if not self.keyword:
                return []
                
            competitor_analyzer = CompetitorAnalyzer(self.keyword)
            competitor_data = competitor_analyzer.analyze_competitors()
            
            type_counts = {}
            type_examples = {}
            for url, schemas in competitor_data.items():
                for schema_type, schema_content in schemas.items():
                    if schema_type not in type_counts:
                        type_counts[schema_type] = 0
                        type_examples[schema_type] = schema_content
                    type_counts[schema_type] += 1
            
            recommendations = []
            
            for schema_type, count in type_counts.items():
                if count > 1:  # Only recommend types used by multiple competitors
                    recommendation = {
                        'type': schema_type,
                        'reason': f'Used by {count} competitors',
                        'example_implementation': type_examples[schema_type],
                        'priority': count
                    }
                    
                    # Add schema type information if available
                    schema_info = self.schema_types_df[self.schema_types_df['Name'] == schema_type]
                    if not schema_info.empty:
                        recommendation['schema_description'] = schema_info['Description'].iloc[0]
                        recommendation['schema_url'] = schema_info['Schema URL'].iloc[0]
                    
                    recommendations.append(recommendation)
            
            return sorted(recommendations, key=lambda x: x['priority'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error in competitor recommendations: {str(e)}")
            return []
