import os
import google.generativeai as genai
from typing import Dict, List, Any, Optional, Union
import json
import time
from functools import lru_cache
import logging
import backoff
from google.api_core import retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GPTSchemaAnalyzer:
    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key not found in environment variables")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.max_retries = 3
        self.base_delay = 1
        
    def _rate_limit_delay(self):
        """Simple rate limiting"""
        time.sleep(1)  # Basic rate limiting
        
    def _convert_to_json_string(self, data: Any) -> Optional[str]:
        """Convert input data to JSON string with improved error handling"""
        try:
            if isinstance(data, str):
                # Validate if string is valid JSON
                json.loads(data)
                return data
            elif isinstance(data, dict):
                return json.dumps(data)
            else:
                raise ValueError(f"Unsupported data type: {type(data)}. Expected dict or valid JSON string.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON conversion error: Invalid JSON format - {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error converting data to JSON: {type(data)} - {str(e)}")
            return None
        
    def _create_analysis_prompt(self, schema_data: str, analysis_type: str) -> str:
        """Create prompts for different types of analysis with improved context"""
        base_prompt = f"""Analyze the following schema.org markup and provide a detailed response:
{schema_data}

Focus on the following aspects:
1. Completeness of implementation
2. Conformance to Schema.org standards
3. Potential for rich results
4. SEO impact

"""
        
        prompts = {
            'documentation': base_prompt + """Compare this implementation against Google's official documentation and Schema.org specifications:
1. List all missing required properties
2. Identify recommended but optional properties
3. Point out any non-standard implementations
4. Suggest specific improvements""",

            'competitors': base_prompt + """Analyze this schema implementation from a competitive perspective:
1. Identify unique approaches
2. List commonly used properties by competitors
3. Highlight potential competitive advantages
4. Suggest improvements based on industry standards""",

            'recommendations': base_prompt + """Generate specific recommendations for improving this schema markup:
1. Priority improvements for SEO impact
2. Changes needed for rich result eligibility
3. Advanced property implementations
4. Best practices and optimization tips"""
        }
        
        return prompts.get(analysis_type, base_prompt)

    @backoff.on_exception(
        backoff.expo,
        (Exception,),
        max_tries=3,
        giveup=lambda e: isinstance(e, ValueError)
    )
    def _make_gemini_request(self, prompt: str) -> str:
        """Make Gemini API request with improved retry logic and error handling"""
        try:
            response = self.model.generate_content(prompt)
            if response.text:
                return response.text
            return "No response generated from the model"
        except Exception as e:
            logger.error(f"Gemini API request failed: {type(e).__name__} - {str(e)}")
            raise
        
    @lru_cache(maxsize=100)
    def analyze_schema_implementation(self, schema_data: Union[Dict, str]) -> Dict[str, Any]:
        """Analyze schema implementation with improved type checking and error handling"""
        try:
            # Type validation and conversion
            if not isinstance(schema_data, (dict, str)):
                raise ValueError(f"Invalid schema_data type: {type(schema_data)}. Expected dict or string.")

            # Convert input to JSON string
            schema_str = self._convert_to_json_string(schema_data)
            if not schema_str:
                return {
                    'error': "Failed to process schema data: Invalid format",
                    'documentation_analysis': "Analysis unavailable - Invalid input format",
                    'competitor_insights': "Analysis unavailable - Invalid input format",
                    'recommendations': "Analysis unavailable - Invalid input format"
                }
            
            analysis_results = {}
            
            for analysis_type in ['documentation', 'competitors', 'recommendations']:
                prompt = self._create_analysis_prompt(schema_str, analysis_type)
                self._rate_limit_delay()
                
                try:
                    result = self._make_gemini_request(prompt)
                    analysis_results[analysis_type] = result
                    
                except Exception as e:
                    error_msg = f"Analysis failed for {analysis_type}: {type(e).__name__} - {str(e)}"
                    logger.error(error_msg)
                    analysis_results[analysis_type] = error_msg
            
            return {
                'documentation_analysis': analysis_results['documentation'],
                'competitor_insights': analysis_results['competitors'],
                'recommendations': analysis_results['recommendations']
            }
            
        except Exception as e:
            error_msg = f"Schema analysis failed: {type(e).__name__} - {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'documentation_analysis': "Analysis unavailable due to error",
                'competitor_insights': "Analysis unavailable due to error",
                'recommendations': "Analysis unavailable due to error"
            }

    def validate_json_ld(self, schema_data: Dict) -> Dict[str, Any]:
        """Validate JSON-LD syntax and structure with improved validation"""
        try:
            validation_results = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Type validation
            if not isinstance(schema_data, dict):
                validation_results['is_valid'] = False
                validation_results['errors'].append(
                    f"Invalid schema data type: expected dict, got {type(schema_data)}"
                )
                return validation_results
            
            # Validate JSON serialization
            try:
                json.dumps(schema_data)
            except Exception as e:
                validation_results['is_valid'] = False
                validation_results['errors'].append(f"Invalid JSON structure: {str(e)}")
                return validation_results
            
            # Check required properties
            required_props = ['@context', '@type']
            for prop in required_props:
                if prop not in schema_data:
                    validation_results['errors'].append(f"Missing required property: {prop}")
                    validation_results['is_valid'] = False
                    
            # Validate @context
            if '@context' in schema_data:
                context = schema_data['@context']
                if context not in ['https://schema.org', 'http://schema.org']:
                    validation_results['warnings'].append(
                        f"Non-standard @context value: {context}. Recommended: 'https://schema.org'"
                    )
                elif context == 'http://schema.org':
                    validation_results['warnings'].append(
                        "Using 'http://schema.org'. Recommended: 'https://schema.org'"
                    )
                    
            return validation_results
            
        except Exception as e:
            logger.error(f"JSON-LD validation error: {type(e).__name__} - {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {type(e).__name__} - {str(e)}"],
                'warnings': []
            }
            
    def generate_property_recommendations(self, schema_type: str) -> Dict[str, Any]:
        """Generate property recommendations with improved structure and error handling"""
        try:
            self._rate_limit_delay()
            
            prompt = f"""For the Schema.org type '{schema_type}', provide detailed structured recommendations:

1. Required Properties:
   - List all mandatory properties with explanations
   - Validation impact and SEO significance
   - Example values and formats

2. Recommended Properties:
   - High-impact optional properties
   - SEO benefits and use cases
   - Implementation priority order
   - Value format examples

3. Rich Results Eligibility:
   - Essential properties for rich results
   - Google Search features enabled
   - Mobile vs Desktop appearance differences
   - Testing tools and validation methods

4. SEO Impact Analysis:
   - Search visibility benefits
   - Competitive advantage opportunities
   - Mobile search implications
   - Voice search optimization

5. Implementation Best Practices:
   - Common implementation errors to avoid
   - Property value formatting guidelines
   - Cross-linking with other schema types
   - Mobile-first considerations

6. Testing & Validation:
   - Google Rich Results Test steps
   - Schema Markup Validator usage
   - Common validation errors and fixes
   - Monitoring recommendations"""

            try:
                result = self._make_gemini_request(prompt)
                return {
                    'success': True,
                    'recommendations': result,
                    'schema_type': schema_type
                }
            
            except Exception as e:
                error_msg = f"Failed to generate recommendations: {type(e).__name__} - {str(e)}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'schema_type': schema_type
                }
                
        except Exception as e:
            error_msg = f"Error in recommendation generation: {type(e).__name__} - {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'schema_type': schema_type
            }
