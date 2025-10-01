"""
Temporary fix for the animal_contained boolean field issue
"""
from typing import Dict, Any, List

def check_missing_fields(context: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    Enhanced version of _get_missing_fields that properly handles boolean values
    
    Args:
        context: The current context dictionary
        required_fields: List of required field names
        
    Returns:
        List of missing field names
    """
    missing = []
    for field in required_fields:
        # Special handling for boolean fields (like animal_contained)
        # which might be False but should be considered as present
        if field == 'animal_contained':
            # Only consider animal_contained missing if it's not in the context at all
            if field not in context:
                missing.append(field)
        else:
            # For other fields, use the standard check
            if not context.get(field):
                missing.append(field)
    return missing
