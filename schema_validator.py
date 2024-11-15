class SchemaValidator:
    def __init__(self, schema_types_df):
        self.schema_types_df = schema_types_df
        
    def validate_schema(self, current_schema):
        """Validate current schema implementation"""
        validation_results = {
            'valid_types': [],
            'invalid_types': [],
            'missing_required_fields': {}
        }
        
        for schema_type in current_schema:
            if schema_type in self.schema_types_df['Name'].values:
                validation_results['valid_types'].append(schema_type)
            else:
                validation_results['invalid_types'].append(schema_type)
                
        return validation_results
        
    def get_missing_schema_types(self, current_schema):
        """Identify potentially beneficial missing schema types"""
        current_types = set(current_schema.keys())
        all_types = set(self.schema_types_df['Name'].values)
        
        # Filter for most relevant missing types
        relevant_types = [
            'Organization', 'WebSite', 'BreadcrumbList', 'Article',
            'Product', 'LocalBusiness', 'FAQPage'
        ]
        
        missing_types = [
            schema_type for schema_type in relevant_types
            if schema_type not in current_types
        ]
        
        return missing_types
        
    def analyze_rich_result_potential(self, current_schema):
        """Analyze potential for rich results"""
        rich_results = {}
        
        # Map schema types to rich result opportunities
        rich_result_mappings = {
            'Product': 'Product Rich Results',
            'Article': 'Article Rich Results',
            'FAQPage': 'FAQ Rich Results',
            'Recipe': 'Recipe Rich Results',
            'Event': 'Event Rich Results',
            'Review': 'Review Rich Results'
        }
        
        for schema_type, rich_result in rich_result_mappings.items():
            if schema_type not in current_schema:
                rich_results[rich_result] = f"Implement {schema_type} schema to enable this rich result"
                
        return rich_results
