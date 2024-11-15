import requests
from bs4 import BeautifulSoup
import json
import re

class SchemaAnalyzer:
    def __init__(self, url):
        self.url = url
        
    def extract_schema(self):
        """Extract schema markup from the given URL"""
        try:
            # Fetch URL content
            response = requests.get(self.url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all script tags with type application/ld+json
            schema_tags = soup.find_all('script', type='application/ld+json')
            
            schema_data = {}
            
            for tag in schema_tags:
                try:
                    data = json.loads(tag.string)
                    if isinstance(data, dict):
                        schema_type = data.get('@type')
                        if schema_type:
                            schema_data[schema_type] = data
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                schema_type = item.get('@type')
                                if schema_type:
                                    schema_data[schema_type] = item
                except json.JSONDecodeError:
                    continue
                    
            return schema_data
            
        except requests.RequestException as e:
            raise Exception(f"Error fetching URL: {str(e)}")
