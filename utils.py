import requests
from typing import Dict, List, Any
import json

def fetch_url_content(url: str) -> str:
    """Fetch content from URL with error handling"""
    try:
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise Exception(f"Error fetching URL: {str(e)}")

def format_schema_data(schema_data: Dict) -> str:
    """Format schema data for display"""
    return json.dumps(schema_data, indent=2)

def clean_schema_type(schema_type: str) -> str:
    """Clean and normalize schema type strings"""
    return schema_type.strip().replace('https://schema.org/', '')
