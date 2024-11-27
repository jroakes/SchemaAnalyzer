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
from validators.base_validator import BaseValidator
from validators.schema_org_validator import SchemaOrgValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaValidator(BaseValidator):
    """Main schema validator class that coordinates different validation strategies."""

    def __init__(self, schema_types_df, keyword: Optional[str] = None):
        """
        Initialize SchemaValidator with necessary components.
        
        Args:
            schema_types_df: DataFrame containing schema type information
            keyword: Optional keyword for competitor analysis
        """
        super().__init__(schema_types_df)
        self.gpt_analyzer = GPTSchemaAnalyzer()
        self.schema_org_validator = SchemaOrgValidator(schema_types_df)
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
