import requests
from functools import lru_cache
import streamlit as st
from gpt_schema_analyzer import GPTSchemaAnalyzer
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

class SchemaValidator:
    def __init__(self, schema_types_df):
        self.schema_types_df = schema_types_df
        self.gpt_analyzer = GPTSchemaAnalyzer()
        self.validation_cache = {}
        self.last_validation_time = {}

    def validate_schema(self, current_schema: Dict[str, Any]) -> Dict[str, Any]:
        try:
            validation_results = {
                'good_schemas': [],
                'needs_improvement': [],
                'suggested_additions': [],
                'all_types': [],
                'errors': [],
                'warnings': []
            }

            for schema_type, schema_data in current_schema.items():
                # Prepare URL-encoded schema data
                schema_json = json.dumps(schema_data)
                encoded_data = urllib.parse.quote(schema_json)
                
                # Call Schema.org validator
                response = requests.get(
                    'https://validator.schema.org/validate',
                    params={'data': encoded_data},
                    headers={'Accept': 'application/json'}
                )
                response.raise_for_status()
                
                # Parse validation response
                validation_data = response.json()
                
                validation_entry = {
                    'type': schema_type,
                    'key': schema_json,
                    'issues': []
                }

                # Process validation results
                if validation_data.get('totalNumErrors', 0) > 0:
                    for node in validation_data.get('nodes', []):
                        for error in node.get('errors', []):
                            validation_entry['issues'].append({
                                'severity': 'error',
                                'message': error.get('message', 'Unknown error')
                            })
                    validation_results['needs_improvement'].append(validation_entry)
                elif validation_data.get('totalNumWarnings', 0) > 0:
                    for node in validation_data.get('nodes', []):
                        for warning in node.get('warnings', []):
                            validation_entry['issues'].append({
                                'severity': 'warning',
                                'message': warning.get('message', 'Unknown warning')
                            })
                    validation_results['needs_improvement'].append(validation_entry)
                else:
                    validation_results['good_schemas'].append(validation_entry)

                validation_results['all_types'].append(schema_type)

                # Add GPT recommendations
                recommendations = self.gpt_analyzer.generate_property_recommendations(schema_type)
                if recommendations.get('success'):
                    validation_entry['recommendations'] = recommendations['recommendations']

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

    def _get_competitor_schema_types(self) -> List[str]:
        """Get list of schema types commonly used by competitors"""
        return ['Organization', 'WebSite', 'BreadcrumbList', 'Product', 'Article']

    def get_schema_description(self, schema_type: str) -> Optional[str]:
        """Get detailed description for a schema type"""
        row = self.schema_types_df[self.schema_types_df['Name'] == schema_type]
        if not row.empty:
            return row['Description'].iloc[0]
        return None

    def get_missing_schema_types(self, current_schema: Dict[str, Any]) -> list:
        """Identify potentially beneficial missing schema types"""
        try:
            current_types = set(clean_schema_type(t) for t in current_schema.keys())
            missing_types = []

            for _, row in self.schema_types_df.iterrows():
                schema_type = row['Name']
                if schema_type not in current_types:
                    missing_types.append({
                        'type': schema_type,
                        'description': row['Description'],
                        'schema_url': row['Schema URL'],
                        'google_doc': row['Google Doc URL'],
                        'recommendations': self.gpt_analyzer.generate_property_recommendations(schema_type)
                    })

            return missing_types

        except Exception as e:
            logger.error(f"Error finding missing schema types: {str(e)}")
            return []

    def analyze_rich_result_potential(self, current_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential for rich results with enhanced GPT analysis"""
        rich_results = {}

        try:
            for schema_type, schema_data in current_schema.items():
                try:
                    normalized_type = clean_schema_type(schema_type)

                    # Ensure proper data handling
                    if isinstance(schema_data, dict):
                        schema_str = json.dumps(schema_data)
                    else:
                        schema_str = str(schema_data)

                    # Get GPT analysis
                    analysis = self.gpt_analyzer.analyze_schema_implementation(schema_str)

                    # Get Google documentation URL
                    google_doc = None
                    if normalized_type in self.schema_types_df['Name'].values:
                        google_doc = self.schema_types_df[
                            self.schema_types_df['Name'] == normalized_type
                        ]['Google Doc URL'].iloc[0]

                    rich_results[normalized_type] = {
                        'potential': analysis.get('recommendations', ''),
                        'current_implementation': analysis.get('documentation_analysis', ''),
                        'competitor_insights': analysis.get('competitor_insights', ''),
                        'google_documentation': google_doc,
                        'validation_timestamp': datetime.now().isoformat()
                    }

                except Exception as e:
                    logger.error(f"Error analyzing rich results for {schema_type}: {str(e)}")
                    rich_results[normalized_type] = {
                        'error': f"Analysis failed: {str(e)}"
                    }

        except Exception as e:
            logger.error(f"Error in rich results analysis: {str(e)}")
            
        return rich_results