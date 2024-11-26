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

class SchemaValidator:
    SCHEMA_VALIDATOR_ENDPOINT = "https://validator.schema.org/validate"

    def __init__(self, schema_types_df, keyword=None):
        self.schema_types_df = schema_types_df
        self.gpt_analyzer = GPTSchemaAnalyzer()
        self.validation_cache = {}
        self.last_validation_time = {}
        self.keyword = keyword

    def _normalize_schema_type(self, schema_type: str) -> str:
        """Normalize schema type to official format"""
        schema_type = schema_type.replace('Website', 'WebSite')
        return schema_type

    def _get_schema_data(self, url: str) -> dict:
        """Get schema data from Schema.org validator"""
        try:
            response = requests.post(self.SCHEMA_VALIDATOR_ENDPOINT, data={"url": url})
            response.raise_for_status()

            if response.text.startswith(")]}'\n"):
                response_text = response.text[5:]
            else:
                response_text = response.text

            data = json.loads(response_text)
            return data
        except requests.RequestException as e:
            logger.error(f"Error fetching URL: {str(e)}")
            raise Exception(f"Error fetching URL: {str(e)}")

    def _extract_schema_data(self, data: dict) -> dict:
        """Extract and process schema data from validator response"""
        response = {'errors': [], 'warnings': [], 'schema_data': {}}

        try:
            for triple_group in data.get('tripleGroups', []):
                for node in triple_group.get('nodes', []):
                    for prop in node.get('properties', []):
                        if prop.get('errors'):
                            response['errors'].extend(prop['errors'])
                        elif prop.get('warnings'):
                            response['warnings'].extend(prop['warnings'])
                        else:
                            response['schema_data'][prop['pred']] = prop['value']
            return response
        except Exception as e:
            logger.error(f"Error extracting schema data: {str(e)}")
            raise Exception(f"Error extracting schema data: {str(e)}")

    def validate_schema(self, current_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schema using Schema.org validator"""
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
                    # Validate using Schema.org validator
                    if isinstance(schema_data, dict) and '@context' in schema_data:
                        schema_url = schema_data['@context']
                        validator_data = self._get_schema_data(schema_url)
                        validation_data = self._extract_schema_data(validator_data)

                        validation_entry = {
                            'type': schema_type,
                            'data': schema_data,
                            'issues': []
                        }

                        # Process validation results
                        if validation_data['errors']:
                            validation_entry['issues'].extend([
                                {'severity': 'error', 'message': error}
                                for error in validation_data['errors']
                            ])
                            validation_results['needs_improvement'].append(validation_entry)
                        else:
                            if validation_data['warnings']:
                                validation_entry['issues'].extend([
                                    {'severity': 'warning', 'message': warning}
                                    for warning in validation_data['warnings']
                                ])
                                validation_results['needs_improvement'].append(validation_entry)
                            else:
                                validation_results['good_schemas'].append(validation_entry)

                        validation_results['all_types'].append(schema_type)

                    else:
                        validation_results['errors'].append({
                            'severity': 'error',
                            'message': f'Invalid schema structure for {schema_type}: Missing @context'
                        })

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
        """Get schema recommendations based on competitor analysis"""
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
                        'google_doc': row['Google Doc URL']
                    })

            return missing_types

        except Exception as e:
            logger.error(f"Error finding missing schema types: {str(e)}")
            return []

    def analyze_rich_result_potential(self, current_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential for rich results"""
        rich_results = {}

        try:
            for schema_type, schema_data in current_schema.items():
                try:
                    normalized_type = clean_schema_type(schema_type)
                    
                    # Get validation results from Schema.org
                    if isinstance(schema_data, dict) and '@context' in schema_data:
                        validator_data = self._get_schema_data(schema_data['@context'])
                        validation_data = self._extract_schema_data(validator_data)
                        
                        # Get Google documentation URL
                        google_doc = None
                        if normalized_type in self.schema_types_df['Name'].values:
                            google_doc = self.schema_types_df[
                                self.schema_types_df['Name'] == normalized_type
                            ]['Google Doc URL'].iloc[0]

                        rich_results[normalized_type] = {
                            'validation_results': validation_data,
                            'google_documentation': google_doc,
                            'validation_timestamp': datetime.now().isoformat()
                        }

                except Exception as e:
                    logger.error(f"Error analyzing rich results for {schema_type}: {str(e)}")
                    rich_results[normalized_type] = {
                        'error': f"Analysis failed: {str(e)}"
                    }
            
            return rich_results

        except Exception as e:
            logger.error(f"Error in rich result analysis: {str(e)}")
            return rich_results