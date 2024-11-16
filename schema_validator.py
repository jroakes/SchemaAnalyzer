import requests
from functools import lru_cache
import streamlit as st
from gpt_schema_analyzer import GPTSchemaAnalyzer
import logging
import json
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
            return f"error_key_{hash(str(data))}"

    def _validate_json_ld_syntax(self, schema_data: Dict) -> Dict[str, Any]:
        """Validate JSON-LD syntax with detailed checks"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }

        try:
            # Check basic structure
            if not isinstance(schema_data, dict):
                validation_result['is_valid'] = False
                validation_result['errors'].append("Schema must be a JSON object")
                return validation_result

            # Required properties check
            required_props = ['@context', '@type']
            for prop in required_props:
                if prop not in schema_data:
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(f"Missing required property: {prop}")

            # Context validation
            if '@context' in schema_data:
                context = schema_data['@context']
                if not isinstance(context, str):
                    validation_result['errors'].append("@context must be a string")
                elif context not in ['https://schema.org', 'http://schema.org']:
                    validation_result['warnings'].append(
                        f"Non-standard @context value: {context}. Use 'https://schema.org'"
                    )

            # Type validation
            if '@type' in schema_data:
                schema_type = schema_data['@type']
                if not isinstance(schema_type, str):
                    validation_result['errors'].append("@type must be a string")
                elif not any(schema_type == row['Name'] for _, row in self.schema_types_df.iterrows()):
                    validation_result['warnings'].append(f"Unknown schema type: {schema_type}")

            # Value type validation
            for key, value in schema_data.items():
                if key not in ['@context', '@type', '@id']:
                    if not isinstance(value, (str, int, float, bool, dict, list)):
                        validation_result['warnings'].append(
                            f"Property '{key}' has unusual value type: {type(value)}"
                        )

            # URL format validation
            url_fields = ['url', 'image', 'logo', 'sameAs']
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
                r'localhost|'  # localhost
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)

            for field in url_fields:
                if field in schema_data:
                    url = schema_data[field]
                    if isinstance(url, str) and not url_pattern.match(url):
                        validation_result['warnings'].append(
                            f"Invalid URL format for {field}: {url}"
                        )

        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")

        return validation_result

    @lru_cache(maxsize=100)
    def _fetch_schema_org_spec(self, schema_type: str) -> Optional[Dict[str, Any]]:
        """Fetch and cache schema.org specifications with rate limiting"""
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
        """Validate schema implementation with enhanced validation and caching"""
        validation_results = {
            'good_schemas': [],
            'needs_improvement': [],
            'suggested_additions': [],
            'all_types': [],
            'errors': [],
            'warnings': [],
            'validation_progress': 0,
            'validation_timestamp': datetime.now().isoformat()
        }

        try:
            if not isinstance(current_schema, dict):
                raise ValueError(f"Input schema must be a dictionary, got {type(current_schema)}")

            if not current_schema:
                validation_results['warnings'].append("Empty schema provided")
                return validation_results

            total_schemas = len(current_schema)
            processed_schemas = 0

            for schema_type, schema_data in current_schema.items():
                try:
                    processed_schemas += 1
                    validation_results['validation_progress'] = (processed_schemas / total_schemas) * 100

                    # Create cache key
                    cache_key = self._make_dict_key(schema_data)

                    # Check cache for recent validation
                    if (
                        cache_key in self.validation_cache
                        and (datetime.now() - self.last_validation_time.get(cache_key, datetime.min)).total_seconds() < 3600
                    ):
                        cached_result = self.validation_cache[cache_key]
                        if cached_result.get('type') == schema_type:
                            if cached_result.get('errors'):
                                validation_results['needs_improvement'].append(cached_result)
                            else:
                                validation_results['good_schemas'].append(cached_result)
                            continue

                    # Perform validation
                    cleaned_type = clean_schema_type(schema_type)
                    validation_results['all_types'].append(cleaned_type)

                    # Syntax validation
                    syntax_validation = self._validate_json_ld_syntax(schema_data)
                    
                    validation_entry = {
                        'type': cleaned_type,
                        'key': cache_key,
                        'issues': [],
                        'recommendations': None
                    }

                    # Add syntax validation issues
                    validation_entry['issues'].extend([
                        {'severity': 'error', 'message': error}
                        for error in syntax_validation['errors']
                    ])
                    validation_entry['issues'].extend([
                        {'severity': 'warning', 'message': warning}
                        for warning in syntax_validation['warnings']
                    ])

                    # Get property recommendations
                    recommendations = self.gpt_analyzer.generate_property_recommendations(cleaned_type)
                    if recommendations.get('success'):
                        validation_entry['recommendations'] = recommendations['recommendations']
                        missing_props = self._check_recommended_properties(schema_data, recommendations)
                        validation_entry['issues'].extend(missing_props)

                    # Categorize the schema
                    if syntax_validation['errors']:
                        validation_results['needs_improvement'].append(validation_entry)
                    elif syntax_validation['warnings'] or missing_props:
                        validation_results['needs_improvement'].append(validation_entry)
                    else:
                        validation_results['good_schemas'].append(validation_entry)

                    # Update cache
                    self.validation_cache[cache_key] = validation_entry
                    self.last_validation_time[cache_key] = datetime.now()

                except Exception as e:
                    logger.error(f"Error processing schema type {schema_type}: {str(e)}")
                    validation_results['errors'].append({
                        'type': schema_type,
                        'error': str(e),
                        'details': f"Error processing schema type: {type(e).__name__}"
                    })

            # Generate suggestions for missing schemas
            competitor_types = self._get_competitor_schema_types()
            current_types = set(validation_results['all_types'])
            added_types = set()  # Track added types to avoid duplicates
            
            for comp_type in competitor_types:
                if comp_type not in current_types and comp_type not in added_types:
                    validation_results['suggested_additions'].append({
                        'type': comp_type,
                        'reason': "Competitor Implementation",
                        'recommendations': self.gpt_analyzer.generate_property_recommendations(comp_type)
                    })
                    added_types.add(comp_type)

        except Exception as e:
            logger.error(f"Error in schema validation: {str(e)}")
            validation_results['errors'].append({
                'error': str(e),
                'type': type(e).__name__,
                'details': "Global validation error occurred"
            })

        return validation_results

    def _check_recommended_properties(self, schema_data: Dict[str, Any], recommendations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for missing recommended properties with improved parsing"""
        missing_props = []
        try:
            rec_text = recommendations['recommendations']
            sections = {
                'required': r'1\.\s*Required Properties:(.*?)(?=2\.)',
                'recommended': r'2\.\s*Recommended Properties:(.*?)(?=3\.)',
                'rich_results': r'3\.\s*Rich Results Properties:(.*?)(?=4\.)'
            }

            for section_type, pattern in sections.items():
                if match := re.search(pattern, rec_text, re.DOTALL):
                    section_text = match.group(1)
                    properties = re.findall(r'-\s*(\w+):', section_text)
                    
                    for prop in properties:
                        if prop not in schema_data:
                            severity = 'error' if section_type == 'required' else 'warning'
                            missing_props.append({
                                'severity': severity,
                                'message': f"Missing {section_type} property: {prop}",
                                'suggestion': f"Add the '{prop}' property to improve {section_type} implementation"
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
            rich_results['error'] = f"Global analysis error: {str(e)}"

        return rich_results