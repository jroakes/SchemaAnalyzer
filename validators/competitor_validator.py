from .base_validator import BaseValidator
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class CompetitorValidator(BaseValidator):
    def __init__(self, schema_types_df=None, gpt_analyzer=None):
        super().__init__(schema_types_df)
        self.gpt_analyzer = gpt_analyzer

    def get_competitor_recommendations(self, competitor_types: List[str]) -> List[Dict[str, Any]]:
        try:
            type_counts = {}
            for schema_type in competitor_types:
                type_counts[schema_type] = competitor_types.count(schema_type)
            
            recommendations = []
            for schema_type, count in type_counts.items():
                if count > 1:
                    recommendations.append({
                        'type': schema_type,
                        'reason': f"Used by {count} competitors",
                        'recommendations': self.gpt_analyzer.generate_property_recommendations(schema_type)
                    })
            
            return sorted(recommendations, key=lambda x: int(x['reason'].split()[2]), reverse=True)
            
        except Exception as e:
            logger.error(f"Error in competitor recommendations: {str(e)}")
            return []
