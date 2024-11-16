import requests
from functools import lru_cache
import streamlit as st
from gpt_schema_analyzer import GPTSchemaAnalyzer
import logging
import json
from utils import clean_schema_type
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaValidator:
    def __init__(self, schema_types_df):
        self.schema_types_df = schema_types_df
        self.gpt_analyzer = GPTSchemaAnalyzer()

    def _make_dict_key(self, data: Union[Dict, Any]) -> str:
        """Convert dictionary to a stable string key with proper nested handling"""
        try:
            if not isinstance(data, (dict, list)):
                return str(data)

            def serialize_nested(obj: Any) -> Any:
                """Helper function to handle nested structures"""
                if isinstance(obj, dict):
                    return {k: serialize_nested(v) for k, v in sorted(obj.items())}
                elif isinstance(obj, list):
                    return [serialize_nested(item) for item in sorted(obj, key=str)]
                elif isinstance(obj, (int, float, str, bool, type(None))):
                    return obj
                else:
                    return str(obj)

            serialized_data = serialize_nested(data)
            return json.dumps(serialized_data, sort_keys=True)
        except Exception as e:
            logger.error(f"Error creating dictionary key: {str(e)}")
            # Fallback to string representation with error indication
            return f"error_key_{hash(str(data))}"

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
        """Validate schema implementation with enhanced error handling and progress tracking"""
        validation_results = {
            'good_schemas': [],
            'needs_improvement': [],
            'suggested_additions': [],
            'all_types': [],
            'competitor_recommendations': [],
            'errors': [],
            'warnings': [],
            'validation_progress': 0
        }

        try:
            if not isinstance(current_schema, dict):
                raise ValueError(f"Input schema must be a dictionary, got {type(current_schema)}")

            if not current_schema:
                validation_results['warnings'].append("Empty schema provided")
                return validation_results

            total_schemas = len(current_schema)
            processed_schemas = 0

            # Process each schema type
            for schema_type, schema_data in current_schema.items():
                try:
                    # Update progress
                    processed_schemas += 1
                    validation_results['validation_progress'] = (processed_schemas / total_schemas) * 100

                    # Type validation for schema_data
                    if not isinstance(schema_data, (dict, str)):
                        raise TypeError(f"Schema data must be a dictionary or string, got {type(schema_data)}")

                    # Create stable key for dictionary values
                    dict_key = self._make_dict_key(schema_data)

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
                        # Check required properties with detailed error messages
                        if '@context' not in schema_data:
                            schema_validation['issues'].append({
                                'severity': 'error',
                                'message': "Missing required @context property",
                                'suggestion': "Add '@context': 'https://schema.org'"
                            })
                            has_errors = True
                        elif schema_data['@context'] not in ['https://schema.org', 'http://schema.org']:
                            schema_validation['issues'].append({
                                'severity': 'warning',
                                'message': f"Non-standard @context value: {schema_data['@context']}",
                                'suggestion': "Use 'https://schema.org' as the @context value"
                            })
                            has_warnings = True

                        if '@type' not in schema_data:
                            schema_validation['issues'].append({
                                'severity': 'error',
                                'message': "Missing required @type property",
                                'suggestion': f"Add '@type': '{cleaned_type}'"
                            })
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
                            schema_validation['issues'].append({
                                'severity': 'warning',
                                'message': "Could not fetch property recommendations",
                                'details': recommendations.get('error', 'Unknown error')
                            })
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
                            'issues': [{
                                'severity': 'error',
                                'message': "Schema data is not a dictionary",
                                'suggestion': "Convert schema data to proper JSON-LD format"
                            }]
                        })

                except Exception as e:
                    logger.error(f"Error processing schema type {schema_type}: {str(e)}")
                    validation_results['errors'].append({
                        'type': schema_type,
                        'error': str(e),
                        'details': f"Error occurred while processing schema type: {type(e).__name__}"
                    })

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
            validation_results['errors'].append({
                'error': str(e),
                'type': type(e).__name__,
                'details': "Global validation error occurred"
            })

        return validation_results

    def _check_recommended_properties(self, schema_data: Dict[str, Any], recommendations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for missing recommended properties with detailed feedback"""
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
                            missing_props.append({
                                'severity': 'warning',
                                'message': f"Missing recommended property: {prop}",
                                'suggestion': f"Consider adding the '{prop}' property to improve completeness"
                            })
        except Exception as e:
            logger.error(f"Error checking recommended properties: {str(e)}")
            missing_props.append({
                'severity': 'info',
                'message': "Error checking recommended properties",
                'details': str(e)
            })
        return missing_props

    def _get_competitor_schema_types(self) -> List[str]:
        """Get list of schema types commonly used by competitors"""
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