import requests
from functools import lru_cache
import streamlit as st

class SchemaValidator:
    def __init__(self, schema_types_df):
        self.schema_types_df = schema_types_df
        
    @lru_cache(maxsize=100)
    def _fetch_schema_org_spec(self, schema_type):
        """Fetch and cache schema.org specifications"""
        try:
            url = f"https://schema.org/{schema_type}"
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except:
            return None

    def get_schema_description(self, schema_type):
        """Get detailed description for a schema type"""
        row = self.schema_types_df[self.schema_types_df['Name'] == schema_type]
        if not row.empty:
            return row['Description'].iloc[0]
        return None
        
    def validate_schema(self, current_schema):
        """Validate current schema implementation"""
        validation_results = {
            'valid_types': [],
            'invalid_types': [],
            'missing_required_fields': {},
            'recommendations': {}
        }
        
        for schema_type in current_schema:
            if schema_type in self.schema_types_df['Name'].values:
                validation_results['valid_types'].append(schema_type)
                # Add specific recommendations
                description = self.get_schema_description(schema_type)
                if description:
                    validation_results['recommendations'][schema_type] = {
                        'description': description,
                        'best_practices': self._get_best_practices(schema_type)
                    }
            else:
                validation_results['invalid_types'].append(schema_type)
                
        return validation_results
        
    def _get_best_practices(self, schema_type):
        """Get best practices for a schema type"""
        best_practices = {
            'Organization': [
                "Include logo and contact information",
                "Specify social media profiles",
                "Add business hours if applicable"
            ],
            'Product': [
                "Include price and availability",
                "Add product images",
                "Specify brand information"
            ],
            'Article': [
                "Include author information",
                "Add publication date",
                "Specify article section"
            ]
        }
        return best_practices.get(schema_type, [])
        
    def get_missing_schema_types(self, current_schema):
        """Identify potentially beneficial missing schema types with tooltips"""
        current_types = set(current_schema.keys())
        missing_types = []
        
        relevant_types = {
            'Organization': "Essential for business websites - helps search engines understand your company information",
            'WebSite': "Enables sitelinks searchbox in search results",
            'BreadcrumbList': "Improves navigation structure visibility in search results",
            'Article': "Important for content-heavy sites - enables rich snippets for articles",
            'Product': "Essential for e-commerce - enables product rich results",
            'LocalBusiness': "Critical for local SEO - enables business information in search results",
            'FAQPage': "Enables FAQ rich results - great for informational pages"
        }
        
        for schema_type, tooltip in relevant_types.items():
            if schema_type not in current_types:
                missing_types.append({
                    'type': schema_type,
                    'tooltip': tooltip,
                    'url': self.schema_types_df[self.schema_types_df['Name'] == schema_type]['Schema URL'].iloc[0],
                    'google_doc': self.schema_types_df[self.schema_types_df['Name'] == schema_type]['Google Doc URL'].iloc[0]
                })
        
        return missing_types
        
    def analyze_rich_result_potential(self, current_schema):
        """Analyze potential for rich results with detailed explanations"""
        rich_results = {}
        
        rich_result_mappings = {
            'Product': {
                'title': 'Product Rich Results',
                'description': 'Displays product information including price, availability, and ratings in search results',
                'requirements': ['price', 'availability', 'review']
            },
            'Article': {
                'title': 'Article Rich Results',
                'description': 'Shows article headline, date, and thumbnail in search results',
                'requirements': ['headline', 'datePublished', 'image']
            },
            'FAQPage': {
                'title': 'FAQ Rich Results',
                'description': 'Displays frequently asked questions directly in search results',
                'requirements': ['question', 'answer']
            },
            'Recipe': {
                'title': 'Recipe Rich Results',
                'description': 'Shows cooking time, ratings, and calories in search results',
                'requirements': ['cookTime', 'nutrition', 'image']
            },
            'Event': {
                'title': 'Event Rich Results',
                'description': 'Displays event details including date, time, and location in search results',
                'requirements': ['startDate', 'location', 'offers']
            },
            'Review': {
                'title': 'Review Rich Results',
                'description': 'Shows star ratings and review snippets in search results',
                'requirements': ['reviewRating', 'author', 'itemReviewed']
            }
        }
        
        for schema_type, details in rich_result_mappings.items():
            if schema_type not in current_schema:
                rich_results[details['title']] = {
                    'message': f"Implement {schema_type} schema to enable this rich result",
                    'description': details['description'],
                    'requirements': details['requirements']
                }
                
        return rich_results
