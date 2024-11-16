import os
import openai
from typing import Dict, List, Any, Optional
import json
import time
from functools import lru_cache
import logging
import backoff

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPTSchemaAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
        openai.api_key = self.api_key
        self.max_retries = 3
        self.base_delay = 1
        
    def _rate_limit_delay(self):
        """Simple rate limiting"""
        time.sleep(1)  # Basic rate limiting
        
    def _convert_to_json_string(self, data: Any) -> Optional[str]:
        """Convert input data to JSON string with error handling"""
        try:
            if isinstance(data, str):
                # Validate if string is valid JSON
                json.loads(data)
                return data
            elif isinstance(data, dict):
                return json.dumps(data)
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON conversion error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error converting data to JSON: {str(e)}")
            return None
        
    def _create_analysis_prompt(self, schema_data: str, analysis_type: str) -> str:
        """Create prompts for different types of analysis"""
        base_prompt = f"Analyze the following schema.org markup:\n{schema_data}\n\n"
        
        prompts = {
            'documentation': base_prompt + "Compare this implementation against Google's official documentation and Schema.org specifications. Identify any missing required properties or potential improvements.",
            'competitors': base_prompt + "Analyze this schema implementation in comparison to common competitor implementations. Identify unique approaches and potential improvements.",
            'recommendations': base_prompt + "Generate specific recommendations for improving this schema markup, focusing on SEO impact and rich result potential."
        }
        
        return prompts.get(analysis_type, base_prompt)

    @backoff.on_exception(backoff.expo, 
                         (openai.error.RateLimitError, 
                          openai.error.APIError,
                          openai.error.ServiceUnavailableError),
                         max_tries=3)
    def _make_openai_request(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """Make OpenAI API request with retry logic"""
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.7,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API request failed: {str(e)}")
            raise
        
    @lru_cache(maxsize=100)
    def analyze_schema_implementation(self, schema_data: Any) -> Dict[str, Any]:
        """Analyze schema implementation using GPT with improved error handling"""
        try:
            # Convert input to JSON string
            schema_str = self._convert_to_json_string(schema_data)
            if not schema_str:
                return {
                    'error': "Failed to process schema data",
                    'documentation_analysis': "Analysis unavailable",
                    'competitor_insights': "Analysis unavailable",
                    'recommendations': "Analysis unavailable"
                }
            
            analysis_results = {}
            
            for analysis_type in ['documentation', 'competitors', 'recommendations']:
                prompt = self._create_analysis_prompt(schema_str, analysis_type)
                self._rate_limit_delay()
                
                try:
                    messages = [
                        {"role": "system", "content": "You are a Schema.org and SEO expert. Analyze the given schema markup and provide detailed insights."},
                        {"role": "user", "content": prompt}
                    ]
                    
                    result = self._make_openai_request(messages)
                    analysis_results[analysis_type] = result
                    
                except Exception as e:
                    logger.error(f"Error in GPT API call for {analysis_type}: {str(e)}")
                    analysis_results[analysis_type] = f"Analysis failed: {str(e)}"
            
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
            
            # Convert dict to string if needed
            if isinstance(schema_data, dict):
                try:
                    json.dumps(schema_data)  # Validate JSON serialization
                except Exception as e:
                    validation_results['is_valid'] = False
                    validation_results['errors'].append(f"Invalid JSON structure: {str(e)}")
                    return validation_results
            
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

            try:
                messages = [
                    {"role": "system", "content": "You are a Schema.org expert. Provide detailed property recommendations."},
                    {"role": "user", "content": prompt}
                ]
                
                result = self._make_openai_request(messages)
                return {
                    'success': True,
                    'recommendations': result
                }
            
            except Exception as e:
                logger.error(f"Error in GPT API call: {str(e)}")
                return {
                    'success': False,
                    'error': f"Failed to generate recommendations: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Error generating property recommendations: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to generate recommendations: {str(e)}"
            }
