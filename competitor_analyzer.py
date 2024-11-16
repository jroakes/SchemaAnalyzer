import requests
import json
from collections import Counter
from schema_analyzer import SchemaAnalyzer
import time
from functools import lru_cache
import os
import random
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CompetitorAnalyzer:
    # List of user agents to rotate through
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59'
    ]
    
    def __init__(self, keyword: str):
        self.keyword = keyword
        self.api_key = os.environ.get('VALUESERP_API_KEY')
        if not self.api_key:
            raise Exception("ValueSerp API key not found in environment variables")
        self.competitor_data = {}
        self.skipped_urls = {}  # Track URLs that were skipped and why
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum time between requests in seconds
        
    def _get_random_user_agent(self) -> str:
        """Get a random user agent from the list"""
        return random.choice(self.USER_AGENTS)
        
    def _rate_limit(self):
        """Implement rate limiting for API requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
            
        self.last_request_time = time.time()

    def _retry_with_backoff(self, func, max_retries: int = 3, initial_delay: float = 1.0) -> Any:
        """Execute a function with exponential backoff retry logic"""
        delay = initial_delay
        
        for retry in range(max_retries):
            try:
                return func()
            except requests.exceptions.RequestException as e:
                if retry == max_retries - 1:
                    raise e
                
                if hasattr(e, 'response'):
                    status_code = e.response.status_code if e.response else None
                    if status_code == 403:
                        logger.warning(f"Received 403 error, retrying with different user agent in {delay} seconds")
                    elif status_code == 429:
                        logger.warning(f"Rate limit exceeded, retrying in {delay} seconds")
                    else:
                        logger.warning(f"Request failed with status {status_code}, retrying in {delay} seconds")
                
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        
        # If we get here, we've exhausted all retries
        raise Exception("Maximum retries exceeded")

    @lru_cache(maxsize=100)
    def get_competitor_urls(self) -> List[str]:
        """Fetch top 10 competitor URLs using ValueSerp API with rate limiting"""
        self._rate_limit()
        
        params = {
            'api_key': self.api_key,
            'q': self.keyword,
            'num': 10,
            'output': 'json'
        }
        
        try:
            def make_request():
                response = requests.get('https://api.valueserp.com/search', params=params)
                response.raise_for_status()
                return response.json()
            
            data = self._retry_with_backoff(make_request)
            
            if 'error' in data:
                raise Exception(f"API Error: {data['error']}")
                
            urls = [result.get('link') for result in data.get('organic_results', [])]
            return urls[:10]  # Ensure we only get top 10
            
        except requests.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    error_msg = "Invalid API key"
                elif e.response.status_code == 429:
                    error_msg = "Rate limit exceeded"
            logger.error(f"Error fetching competitor URLs: {error_msg}")
            raise Exception(f"Error fetching competitor URLs: {error_msg}")
            
    def analyze_competitors(self, progress_callback=None) -> Dict[str, Any]:
        """Analyze schema markup from competitor URLs with progress tracking"""
        competitor_urls = self.get_competitor_urls()
        total_urls = len(competitor_urls)
        successful_analyses = 0
        
        for idx, url in enumerate(competitor_urls, 1):
            try:
                if progress_callback:
                    progress_callback(idx / total_urls)
                    
                def analyze_url():
                    headers = {'User-Agent': self._get_random_user_agent()}
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    analyzer = SchemaAnalyzer(url)
                    return analyzer.extract_schema()
                
                schema_data = self._retry_with_backoff(analyze_url)
                self.competitor_data[url] = schema_data
                successful_analyses += 1
                
                # Rate limit between competitor analysis
                time.sleep(1)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error analyzing {url}: {error_msg}")
                
                # Track skipped URLs and reasons
                if "403" in error_msg:
                    reason = "Access forbidden - Website blocks automated access"
                elif "404" in error_msg:
                    reason = "Page not found"
                elif "timeout" in error_msg.lower():
                    reason = "Request timed out"
                else:
                    reason = f"Error: {error_msg}"
                
                self.skipped_urls[url] = reason
                continue
                
        if successful_analyses == 0:
            logger.warning("No competitor analyses were successful")
        else:
            logger.info(f"Successfully analyzed {successful_analyses}/{total_urls} competitor URLs")
            
        return self.competitor_data
        
    def get_schema_usage_stats(self) -> List[Dict[str, Any]]:
        """Get statistics about schema usage among competitors"""
        schema_types = []
        
        for url, schemas in self.competitor_data.items():
            schema_types.extend(schemas.keys())
            
        usage_counts = Counter(schema_types)
        total_sites = len(self.competitor_data)
        
        stats = [
            {
                'schema_type': schema_type,
                'usage_count': count,
                'percentage': (count / total_sites) * 100 if total_sites else 0
            }
            for schema_type, count in usage_counts.most_common()
        ]
        
        return stats
        
    def get_competitor_insights(self) -> List[Dict[str, Any]]:
        """Get detailed insights about competitor schema usage"""
        insights = []
        schema_types = []
        
        for url, schemas in self.competitor_data.items():
            schema_types.extend(schemas.keys())
            
        total_competitors = len(self.competitor_data)
        usage_counts = Counter(schema_types)
        
        for schema_type, count in usage_counts.most_common():
            usage_percentage = (count / total_competitors) * 100 if total_competitors > 0 else 0
            insights.append({
                'schema_type': schema_type,
                'count': count,
                'percentage': usage_percentage,
                'recommendation': f"{schema_type} is used by {usage_percentage:.1f}% of competitors"
            })
            
        return insights

    def get_skipped_urls(self) -> Dict[str, str]:
        """Get URLs that were skipped during analysis and the reasons why"""
        return self.skipped_urls
