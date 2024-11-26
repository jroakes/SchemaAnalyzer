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

            if not current_schema:
                validation_results['warnings'].append('No schema data found on the page')
                # Get competitor recommendations when no schema is found
                competitor_recommendations = self._get_competitor_recommendations(current_schema=None)
                if competitor_recommendations:
                    validation_results['suggested_additions'] = competitor_recommendations
                return validation_results

            # Update schema type normalization
            normalized_schema = {}
            for schema_type, schema_data in current_schema.items():
                normalized_type = self._normalize_schema_type(schema_type)
                normalized_schema[normalized_type] = schema_data

            for schema_type, schema_data in normalized_schema.items():
                validation_entry = {
                    'type': schema_type,
                    'key': json.dumps(schema_data),
                    'issues': []
                }

                try:
                    # Basic JSON-LD validation
                    if '@type' not in schema_data:
                        validation_entry['issues'].append({
                            'severity': 'error',
                            'message': 'Missing required @type property'
                        })

                    if '@context' not in schema_data:
                        validation_entry['issues'].append({
                            'severity': 'error',
                            'message': 'Missing required @context property'
                        })

                    # Add GPT recommendations regardless of validation status
                    recommendations = self.gpt_analyzer.generate_property_recommendations(schema_type)
                    if recommendations.get('success'):
                        validation_entry['recommendations'] = recommendations['recommendations']

                    # Classify based on issues
                    if validation_entry['issues']:
                        validation_results['needs_improvement'].append(validation_entry)
                    else:
                        validation_results['good_schemas'].append(validation_entry)

                    validation_results['all_types'].append(schema_type)

                except Exception as e:
                    logger.error(f"Error validating schema {schema_type}: {str(e)}")
                    validation_entry['issues'].append({
                        'severity': 'error',
                        'message': f'Validation error: {str(e)}'
                    })
                    validation_results['needs_improvement'].append(validation_entry)

            # Add suggested schemas based on competitor analysis
            competitor_types = self._get_competitor_schema_types()
            current_types = set(schema_type for schema_type in normalized_schema.keys())
            
            for comp_type in competitor_types:
                if comp_type not in current_types:
                    validation_results['suggested_additions'].append({
                        'type': comp_type,
                        'reason': "Competitor Implementation",
                        'recommendations': self.gpt_analyzer.generate_property_recommendations(comp_type)
                    })

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
        if not self.keyword:
            return ['Organization', 'WebSite', 'BreadcrumbList', 'Product', 'Article']
            
        competitor_analyzer = CompetitorAnalyzer(self.keyword)
        competitor_data = competitor_analyzer.analyze_competitors()
        
        # Count schema usage among competitors
        type_counts = {}
        for url, schemas in competitor_data.items():
            for schema_type in schemas.keys():
                type_counts[schema_type] = type_counts.get(schema_type, 0) + 1
        
        # Only return types used by multiple competitors
        return [
            schema_type for schema_type, count in type_counts.items()
            if count > 1  # Only include types used by multiple competitors
        ]

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
            
            return rich_results

        except Exception as e:
            logger.error(f"Error in rich result analysis: {str(e)}")
            return rich_results

    def _get_competitor_recommendations(self, current_schema: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        try:
            if not self.keyword:
                return []
                
            # Initialize CompetitorAnalyzer with keyword
            competitor_analyzer = CompetitorAnalyzer(self.keyword)
            
            # Get competitor data
            competitor_data = competitor_analyzer.analyze_competitors()
            
            # Count schema usage among competitors
            type_counts = {}
            for url, schemas in competitor_data.items():
                for schema_type in schemas.keys():
                    normalized_type = self._normalize_schema_type(schema_type)
                    type_counts[normalized_type] = type_counts.get(normalized_type, 0) + 1
            
            # Generate recommendations for types used by multiple competitors
            recommendations = []
            current_types = set(current_schema.keys()) if current_schema else set()
            
            for schema_type, count in type_counts.items():
                if count > 1:  # Only include types used by multiple competitors
                    if not current_schema or schema_type not in current_types:
                        recommendations.append({
                            'type': schema_type,
                            'reason': f"Used by {count} competitors",
                            'recommendations': self.gpt_analyzer.generate_property_recommendations(schema_type)
                        })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in competitor recommendations: {str(e)}")
            return []
