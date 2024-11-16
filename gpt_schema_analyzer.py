import os
import openai
from typing import Dict, List, Any
import json
import time
from functools import lru_cache
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPTSchemaAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        openai.api_key = self.api_key
        
    def _rate_limit_delay(self):
        """Simple rate limiting"""
        time.sleep(1)  # Basic rate limiting
        
    def _create_analysis_prompt(self, schema_data: Dict, analysis_type: str) -> str:
        """Create prompts for different types of analysis"""
        base_prompt = f"Analyze the following schema.org markup:\n{json.dumps(schema_data, indent=2)}\n\n"
        
        prompts = {
            'documentation': base_prompt + "Compare this implementation against Google's official documentation and Schema.org specifications. Identify any missing required properties or potential improvements.",
            'competitors': base_prompt + "Analyze this schema implementation in comparison to common competitor implementations. Identify unique approaches and potential improvements.",
            'recommendations': base_prompt + "Generate specific recommendations for improving this schema markup, focusing on SEO impact and rich result potential."
        }
        
        return prompts.get(analysis_type, base_prompt)
        
    @lru_cache(maxsize=100)
    def analyze_schema_implementation(self, schema_data: Dict) -> Dict[str, Any]:
        """Analyze schema implementation using GPT"""
        try:
            analysis_results = {}
            
            for analysis_type in ['documentation', 'competitors', 'recommendations']:
                prompt = self._create_analysis_prompt(schema_data, analysis_type)
                
                self._rate_limit_delay()
                
                response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a Schema.org and SEO expert. Analyze the given schema markup and provide detailed insights."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                analysis_results[analysis_type] = response.choices[0].message.content
                
            return {
                'documentation_analysis': analysis_results['documentation'],
                'competitor_insights': analysis_results['competitors'],
                'recommendations': analysis_results['recommendations']
            }
            
        except Exception as e:
            logger.error(f"Error in GPT analysis: {str(e)}")
            return {
                'error': f"Failed to analyze schema: {str(e)}",
                'documentation_analysis': "Analysis unavailable",
                'competitor_insights': "Analysis unavailable",
                'recommendations': "Analysis unavailable"
            }
            
    def validate_json_ld(self, schema_data: Dict) -> Dict[str, Any]:
        """Validate JSON-LD syntax and structure"""
        try:
            validation_results = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Basic structure validation
            if not isinstance(schema_data, dict):
                validation_results['is_valid'] = False
                validation_results['errors'].append("Schema must be a JSON object")
                return validation_results
                
            # Check for required basic properties
            required_props = ['@context', '@type']
            for prop in required_props:
                if prop not in schema_data:
                    validation_results['errors'].append(f"Missing required property: {prop}")
                    validation_results['is_valid'] = False
                    
            # Validate @context
            if '@context' in schema_data:
                if schema_data['@context'] != 'https://schema.org' and schema_data['@context'] != 'http://schema.org':
                    validation_results['warnings'].append("@context should be 'https://schema.org'")
                    
            return validation_results
            
        except Exception as e:
            logger.error(f"Error in JSON-LD validation: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
            
    def generate_property_recommendations(self, schema_type: str) -> Dict[str, Any]:
        """Generate property recommendations for a given schema type"""
        try:
            self._rate_limit_delay()
            
            prompt = f"""For the Schema.org type '{schema_type}', provide:
1. Required properties
2. Recommended properties
3. Properties that enable rich results
4. Common implementation mistakes to avoid"""

            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a Schema.org expert. Provide detailed property recommendations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return {
                'success': True,
                'recommendations': response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Error generating property recommendations: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to generate recommendations: {str(e)}"
            }
