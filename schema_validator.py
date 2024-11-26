from functools import lru_cache
import streamlit as st
from gpt_schema_analyzer import GPTSchemaAnalyzer
from competitor_analyzer import CompetitorAnalyzer
from validators.schema_org_validator import SchemaOrgValidator
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

    def _validate_with_schema_org(self, url: str) -> Dict[str, Any]:
        """Validate schema using official Schema.org validator"""
        validator = SchemaOrgValidator()
        return validator.validate_with_schema_org(url)

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
                validation_results['warnings'].append({
                    'severity': 'warning',
                    'message': 'No schema data found on the page',
                    'suggestion': 'Consider implementing schema markup to improve search visibility'
                })
                
                competitor_recommendations = self._get_competitor_recommendations(current_schema=None)
                if competitor_recommendations:
                    top_recommendations = sorted(
                        competitor_recommendations, 
                        key=lambda x: x.get('priority', 0), 
                        reverse=True
                    )[:5]
                    
                    for rec in top_recommendations:
                        validation_results['suggested_additions'].append({
                            'type': rec['type'],
                            'reason': rec['reason'],
                            'recommendations': rec['recommendations'],
                            'example_implementation': rec['example_implementation'],
                            'schema_description': rec.get('schema_description', ''),
                            'schema_url': rec.get('schema_url', ''),
                            'priority': rec.get('priority', 0)
                        })
                    
                    validation_results['summary'] = (
                        f"Found {len(top_recommendations)} recommended schema types based on "
                        f"competitor analysis. Top recommendation: {top_recommendations[0]['type']} "
                        f"({top_recommendations[0]['reason']})"
                    )
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
                    # Validate using Schema.org validator
                    schema_org_validation = self._validate_with_schema_org(schema_data.get('@context', ''))
                    
                    if not schema_org_validation['is_valid']:
                        validation_entry['issues'].extend([
                            {'severity': 'error', 'message': error}
                            for error in schema_org_validation['errors']
                        ])
                    
                    validation_entry['warnings'] = schema_org_validation['warnings']

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
                if count > 1:
                    gpt_recommendations = self.gpt_analyzer.generate_property_recommendations(schema_type)
                    example_schema = type_examples[schema_type]
                    
                    recommendation = {
                        'type': schema_type,
                        'reason': f'Used by {count} competitors',
                        'recommendations': gpt_recommendations,
                        'example_implementation': example_schema,
                        'priority': count
                    }
                    
                    schema_info = self.schema_types_df[self.schema_types_df['Name'] == schema_type]
                    if not schema_info.empty:
                        recommendation['schema_description'] = schema_info['Description'].iloc[0]
                        recommendation['schema_url'] = schema_info['Schema URL'].iloc[0]
                    
                    recommendations.append(recommendation)
            
            recommendations.sort(key=lambda x: x['priority'], reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error in competitor recommendations: {str(e)}")
            return []