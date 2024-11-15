import requests
import json
from collections import Counter
from schema_analyzer import SchemaAnalyzer
import time
from functools import lru_cache
import os

class CompetitorAnalyzer:
    def __init__(self, keyword):
        self.keyword = keyword
        self.api_key = os.environ.get('VALUESERP_API_KEY')
        if not self.api_key:
            raise Exception("ValueSerp API key not found in environment variables")
        self.competitor_data = {}
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum time between requests in seconds
        
    def _rate_limit(self):
        """Implement rate limiting for API requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
            
        self.last_request_time = time.time()

    @lru_cache(maxsize=100)
    def get_competitor_urls(self):
        """Fetch top 10 competitor URLs using ValueSerp API with rate limiting"""
        self._rate_limit()
        
        params = {
            'api_key': self.api_key,
            'q': self.keyword,
            'num': 10,
            'output': 'json'
        }
        
        try:
            response = requests.get('https://api.valueserp.com/search', params=params)
            if response.status_code == 429:  # Too Many Requests
                time.sleep(5)  # Wait for 5 seconds before retrying
                return self.get_competitor_urls()
                
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                raise Exception(f"API Error: {data['error']}")
                
            # Extract organic results URLs
            urls = [result.get('link') for result in data.get('organic_results', [])]
            return urls[:10]  # Ensure we only get top 10
            
        except requests.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 401:
                    error_msg = "Invalid API key"
                elif e.response.status_code == 429:
                    error_msg = "Rate limit exceeded"
            raise Exception(f"Error fetching competitor URLs: {error_msg}")
            
    def analyze_competitors(self, progress_callback=None):
        """Analyze schema markup from competitor URLs with progress tracking"""
        competitor_urls = self.get_competitor_urls()
        total_urls = len(competitor_urls)
        
        for idx, url in enumerate(competitor_urls, 1):
            try:
                if progress_callback:
                    progress_callback(idx / total_urls)
                    
                analyzer = SchemaAnalyzer(url)
                schema_data = analyzer.extract_schema()
                self.competitor_data[url] = schema_data
                
                # Rate limit between competitor analysis
                time.sleep(1)
            except Exception as e:
                print(f"Error analyzing {url}: {str(e)}")
                continue
                
        return self.competitor_data
        
    def get_schema_usage_stats(self):
        """Get statistics about schema usage among competitors"""
        schema_types = []
        
        for url, schemas in self.competitor_data.items():
            schema_types.extend(schemas.keys())
            
        usage_counts = Counter(schema_types)
        
        stats = [
            {
                'schema_type': schema_type,
                'usage_count': count,
                'percentage': (count / len(self.competitor_data)) * 100 if self.competitor_data else 0
            }
            for schema_type, count in usage_counts.most_common()
        ]
        
        return stats

    def get_competitor_insights(self):
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
