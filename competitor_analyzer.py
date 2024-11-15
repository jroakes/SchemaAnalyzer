import requests
import json
from collections import Counter
from schema_analyzer import SchemaAnalyzer

class CompetitorAnalyzer:
    def __init__(self, keyword):
        self.keyword = keyword
        self.api_key = 'E1DCFF8C9B88423D94750D2E791D70F7'
        self.competitor_data = {}
        
    def get_competitor_urls(self):
        """Fetch top 10 competitor URLs using ValueSerp API"""
        params = {
            'api_key': self.api_key,
            'q': self.keyword,
            'num': 10
        }
        
        try:
            response = requests.get('https://api.valueserp.com/search', params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract organic results URLs
            urls = [result.get('link') for result in data.get('organic_results', [])]
            return urls[:10]  # Ensure we only get top 10
            
        except requests.RequestException as e:
            raise Exception(f"Error fetching competitor URLs: {str(e)}")
            
    def analyze_competitors(self):
        """Analyze schema markup from competitor URLs"""
        competitor_urls = self.get_competitor_urls()
        
        for url in competitor_urls:
            try:
                analyzer = SchemaAnalyzer(url)
                schema_data = analyzer.extract_schema()
                self.competitor_data[url] = schema_data
            except Exception:
                continue
                
        return self.competitor_data
        
    def get_schema_usage_stats(self):
        """Get statistics about schema usage among competitors"""
        schema_types = []
        
        for url, schemas in self.competitor_data.items():
            schema_types.extend(schemas.keys())
            
        usage_counts = Counter(schema_types)
        
        return [
            {'schema_type': schema_type, 'usage_count': count}
            for schema_type, count in usage_counts.most_common()
        ]
