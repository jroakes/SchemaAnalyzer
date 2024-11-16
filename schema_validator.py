import requests
from functools import lru_cache
import streamlit as st
from gpt_schema_analyzer import GPTSchemaAnalyzer
import logging
import json
from utils import clean_schema_type
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaValidator:
    def __init__(self, schema_types_df):
        self.schema_types_df = schema_types_df
        self.gpt_analyzer = GPTSchemaAnalyzer()

    def _make_dict_key(self, data: Dict) -> str:
        """Convert dictionary to a stable string key"""
        try:
            # Sort dictionary items to ensure consistent serialization
            sorted_dict = dict(sorted(data.items()))
            return json.dumps(sorted_dict, sort_keys=True)
        except Exception as e:
            logger.error(f"Error creating dictionary key: {str(e)}")
            return str(hash(str(data)))

    @lru_cache(maxsize=100)
    def _fetch_schema_org_spec(self, schema_type: str) -> Optional[Dict[str, Any]]:
        """Fetch and cache schema.org specifications"""
        try:
            url = f"https://schema.org/{schema_type}"
            response = requests.get(url)
            response.raise_for_status()
            return {
                'url': url,
                'status': 'success',
                'type': schema_type,
                'content': response.text
            }
        except Exception as e:
            logger.error(f"Error fetching schema spec: {str(e)}")
            return None

    def validate_schema(self, current_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schema implementation with enhanced categorization"""
        validation_results = {
            'good_schemas': [],
            'needs_improvement': [],
            'suggested_additions': [],
            'all_types': [],
            'competitor_recommendations': [],
            'errors': [],
            'warnings': []
        }

        try:
            if not isinstance(current_schema, dict):
                raise ValueError("Input schema must be a dictionary")

            if not current_schema:
                validation_results['warnings'].append("Empty schema provided")
                return validation_results

            # Process each schema type
            for schema_type, schema_data in current_schema.items():
                try:
                    # Create stable key for dictionary values
                    if isinstance(schema_data, dict):
                        dict_key = self._make_dict_key(schema_data)
                    else:
                        dict_key = str(schema_data)

                    # Clean and validate schema type
                    cleaned_type = clean_schema_type(schema_type)
                    validation_results['all_types'].append(cleaned_type)

                    # Basic validation checks
                    has_errors = False
                    has_warnings = False
                    schema_validation = {
                        'type': cleaned_type,
                        'key': dict_key,
                        'issues': []
                    }

                    # Validate schema data
                    if isinstance(schema_data, dict):
                        # Check required properties
                        if '@context' not in schema_data:
                            schema_validation['issues'].append("Missing @context property")
                            has_errors = True
                        elif schema_data['@context'] not in ['https://schema.org', 'http://schema.org']:
                            schema_validation['issues'].append("Non-standard @context value")
                            has_warnings = True

                        if '@type' not in schema_data:
                            schema_validation['issues'].append("Missing @type property")
                            has_errors = True

                        # Get recommendations
                        recommendations = self.gpt_analyzer.generate_property_recommendations(cleaned_type)
                        if recommendations.get('success'):
                            missing_props = self._check_recommended_properties(schema_data, recommendations)
                            if missing_props:
                                schema_validation['issues'].extend(missing_props)
                                has_warnings = True
                            schema_validation['recommendations'] = recommendations['recommendations']
                        else:
                            schema_validation['issues'].append("Could not fetch recommendations")
                            has_warnings = True

                        # Categorize the schema
                        if has_errors:
                            validation_results['needs_improvement'].append(schema_validation)
                        elif has_warnings:
                            validation_results['needs_improvement'].append(schema_validation)
                        else:
                            validation_results['good_schemas'].append(schema_validation)

                    else:
                        validation_results['needs_improvement'].append({
                            'type': cleaned_type,
                            'key': dict_key,
                            'issues': ["Schema data is not a dictionary"]
                        })

                except Exception as e:
                    logger.error(f"Error processing schema type {schema_type}: {str(e)}")
                    validation_results['errors'].append(f"Error processing {schema_type}: {str(e)}")

            # Add competitor-based suggestions
            competitor_types = self._get_competitor_schema_types()
            current_types = set(validation_results['all_types'])
            for comp_type in competitor_types:
                if comp_type not in current_types:
                    validation_results['suggested_additions'].append({
                        'type': comp_type,
                        'reason': "Used by competitors",
                        'recommendations': self.gpt_analyzer.generate_property_recommendations(comp_type)
                    })

        except Exception as e:
            logger.error(f"Error in schema validation: {str(e)}")
            validation_results['errors'].append(f"Schema validation error: {str(e)}")

        return validation_results

    def _check_recommended_properties(self, schema_data: Dict[str, Any], recommendations: Dict[str, Any]) -> List[str]:
        """Check for missing recommended properties"""
        missing_props = []
        try:
            # Parse recommendations text for required and recommended properties
            rec_text = recommendations['recommendations']
            if 'Required Properties:' in rec_text:
                required_section = rec_text.split('Required Properties:')[1].split('2.')[0]
                for line in required_section.split('\n'):
                    if '-' in line:
                        prop = line.split('-')[1].strip().split(' ')[0]
                        if prop and prop not in schema_data:
                            missing_props.append(f"Missing required property: {prop}")
        except Exception as e:
            logger.error(f"Error checking recommended properties: {str(e)}")
        return missing_props

    def _get_competitor_schema_types(self) -> List[str]:
        """Get list of schema types commonly used by competitors"""
        # This would be populated from competitor analysis
        # For now, returning a sample list
        return ['Organization', 'WebSite', 'BreadcrumbList']

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
        """Analyze potential for rich results with GPT-enhanced insights"""
        rich_results = {}

        for schema_type, schema_data in current_schema.items():
            try:
                normalized_type = clean_schema_type(schema_type)

                # Ensure proper data handling
                if isinstance(schema_data, dict):
                    schema_str = json.dumps(schema_data)
                else:
                    schema_str = str(schema_data)

                analysis = self.gpt_analyzer.analyze_schema_implementation(schema_str)

                rich_results[normalized_type] = {
                    'potential': analysis.get('recommendations', ''),
                    'current_implementation': analysis.get('documentation_analysis', ''),
                    'competitor_insights': analysis.get('competitor_insights', ''),
                    'google_documentation': self.schema_types_df[
                        self.schema_types_df['Name'] == normalized_type
                    ]['Google Doc URL'].iloc[0] if normalized_type in self.schema_types_df['Name'].values else None
                }

            except Exception as e:
                logger.error(f"Error analyzing rich results for {schema_type}: {str(e)}")
                rich_results[normalized_type] = {
                    'error': f"Analysis failed: {str(e)}"
                }

        return rich_results