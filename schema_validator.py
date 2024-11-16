import requests
from functools import lru_cache
import streamlit as st
from gpt_schema_analyzer import GPTSchemaAnalyzer
import logging
import json
from utils import clean_schema_type
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaValidator:
    def __init__(self, schema_types_df):
        self.schema_types_df = schema_types_df
        self.gpt_analyzer = GPTSchemaAnalyzer()
        
    @lru_cache(maxsize=100)
    def _fetch_schema_org_spec(self, schema_type: str) -> Optional[Dict[str, Any]]:
        """Fetch and cache schema.org specifications with improved dictionary handling"""
        try:
            url = f"https://schema.org/{schema_type}"
            response = requests.get(url)
            response.raise_for_status()
            
            # Try to parse as JSON-LD if available
            content_type = response.headers.get('content-type', '')
            if 'application/ld+json' in content_type:
                return response.json()
            
            # Return structured data even for HTML response
            return {
                'url': url,
                'status': 'success',
                'type': schema_type,
                'raw_content': response.text
            }
        except requests.RequestException as e:
            logger.error(f"Error fetching schema spec for {schema_type}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing schema spec JSON for {schema_type}: {str(e)}")
            return None

    def get_schema_description(self, schema_type: str) -> Optional[str]:
        """Get detailed description for a schema type"""
        row = self.schema_types_df[self.schema_types_df['Name'] == schema_type]
        if not row.empty:
            return row['Description'].iloc[0]
        return None
        
    def validate_schema(self, current_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate current schema implementation with enhanced dictionary handling"""
        validation_results = {
            'valid_types': [],
            'invalid_types': [],
            'syntax_validation': {},
            'gpt_analysis': {},
            'property_recommendations': {},
            'warnings': [],
            'errors': []
        }
        
        try:
            # Input type validation
            if not isinstance(current_schema, dict):
                raise ValueError("Input schema must be a dictionary")

            if not current_schema:
                validation_results['warnings'].append("Empty schema provided")
                return validation_results

            # Process each schema type
            for raw_type, schema_data in current_schema.items():
                try:
                    # Normalize schema type
                    schema_type = clean_schema_type(raw_type)
                    
                    # Validate schema data type
                    if not isinstance(schema_data, (dict, str)):
                        validation_results['errors'].append(
                            f"Invalid data type for {schema_type}: expected dict or string, got {type(schema_data)}"
                        )
                        continue

                    # Convert string to dict if needed
                    if isinstance(schema_data, str):
                        try:
                            schema_data = json.loads(schema_data)
                        except json.JSONDecodeError as e:
                            validation_results['errors'].append(
                                f"Invalid JSON string for {schema_type}: {str(e)}"
                            )
                            continue

                    # Basic type validation
                    if schema_type in self.schema_types_df['Name'].values:
                        validation_results['valid_types'].append(schema_type)
                        
                        # JSON-LD syntax validation
                        syntax_validation = self.gpt_analyzer.validate_json_ld(schema_data)
                        validation_results['syntax_validation'][schema_type] = syntax_validation
                        
                        # GPT-powered analysis
                        gpt_analysis = self.gpt_analyzer.analyze_schema_implementation(schema_data)
                        validation_results['gpt_analysis'][schema_type] = gpt_analysis
                        
                        # Property recommendations
                        prop_recommendations = self.gpt_analyzer.generate_property_recommendations(schema_type)
                        validation_results['property_recommendations'][schema_type] = prop_recommendations
                        
                        # Add warnings and errors from validations
                        if syntax_validation.get('warnings'):
                            validation_results['warnings'].extend(
                                [f"{schema_type}: {w}" for w in syntax_validation['warnings']]
                            )
                        if syntax_validation.get('errors'):
                            validation_results['errors'].extend(
                                [f"{schema_type}: {e}" for e in syntax_validation['errors']]
                            )
                    else:
                        validation_results['invalid_types'].append(schema_type)
                        validation_results['errors'].append(f"Invalid schema type: {schema_type}")
                        
                except Exception as e:
                    logger.error(f"Error processing schema type {raw_type}: {str(e)}")
                    validation_results['errors'].append(f"Error processing {raw_type}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in schema validation: {str(e)}")
            validation_results['errors'].append(f"Schema validation error: {str(e)}")
            
        return validation_results

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
