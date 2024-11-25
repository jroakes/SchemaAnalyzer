from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class BaseValidator:
    def __init__(self, schema_types_df=None):
        self.schema_types_df = schema_types_df
