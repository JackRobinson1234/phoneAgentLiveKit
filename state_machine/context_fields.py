from enum import Enum, auto
from typing import Dict, Any, Optional, List

class ContextField(Enum):
    """Enum of all possible context fields that can be stored in the conversation context"""
    
    # General fields
    DETECTED_INTENT = "detected_intent"
    SERVICE_TYPE = "service_type"
    URGENCY_LEVEL = "urgency_level"
    TURN_COUNT = "turn_count"
    
    # Animal information
    ANIMAL_TYPE = "animal_type"
    ANIMAL_NAME = "animal_name"
    ANIMAL_BREED = "animal_breed"
    ANIMAL_AGE = "animal_age"
    ANIMAL_GENDER = "animal_gender"
    ANIMAL_COLOR = "animal_color"
    ANIMAL_SIZE = "animal_size"
    ANIMAL_WEIGHT = "animal_weight"
    ANIMAL_DESCRIPTION = "animal_description"
    ANIMAL_CONDITION = "animal_condition"
    ANIMAL_CONTAINED = "animal_contained"
    IDENTIFYING_FEATURES = "identifying_features"
    MICROCHIPPED = "microchipped"
    COLLAR = "collar"
    TAGS = "tags"
    
    # Location information
    LOCATION = "location"
    LOCATION_FOUND = "location_found"
    LAST_SEEN_LOCATION = "last_seen_location"
    LAST_SEEN_TIME = "last_seen_time"
    
    # Contact information
    OWNER_NAME = "owner_name"
    OWNER_CONTACT = "owner_contact"
    FINDER_NAME = "finder_name"
    FINDER_CONTACT = "finder_contact"
    FINDER_CAN_KEEP = "finder_can_keep"
    
    # Pet surrender information
    SURRENDER_REASON = "surrender_reason"
    HEALTH_ISSUES = "health_issues"
    BEHAVIORAL_ISSUES = "behavioral_issues"
    SELECTED_DATE = "selected_date"
    
    # Case information
    CASE_ID = "case_id"
    CASE_TYPE = "case_type"
    CASE_STATUS = "case_status"
    CASE_DETAILS = "case_details"
    EXISTING_CASE_ID = "existing_case_id"
    
    # Metadata
    TIMESTAMP = "timestamp"
    AUTO_ADVANCE = "auto_advance"
    NEXT_STATE = "next_state"
    ERROR_MESSAGE = "error_message"
    
    # Aliases and alternative names
    CONDITION = "condition"  # Alias for ANIMAL_CONDITION
    HEALTH_STATUS = "health_status"  # Alias for ANIMAL_CONDITION
    SEVERITY = "severity"  # Related to ANIMAL_CONDITION
    EMERGENCY_STATUS = "emergency_status"  # Related to URGENCY_LEVEL
    
    @classmethod
    def get_aliases(cls) -> Dict[str, List[str]]:
        """Get mapping of primary fields to their aliases"""
        return {
            cls.ANIMAL_CONDITION.value: [cls.CONDITION.value, cls.HEALTH_STATUS.value, cls.SEVERITY.value],
            cls.URGENCY_LEVEL.value: [cls.EMERGENCY_STATUS.value],
            cls.ANIMAL_CONTAINED.value: ["contained"],
            cls.ANIMAL_DESCRIPTION.value: ["description"],
            cls.OWNER_CONTACT.value: ["contact", "phone", "email"],
        }
    
    @classmethod
    def normalize_field(cls, field: str) -> str:
        """Convert any field name to its canonical form"""
        # If it's already a canonical field, return it
        if field in [e.value for e in cls]:
            return field
            
        # Check aliases
        for primary, aliases in cls.get_aliases().items():
            if field in aliases:
                return primary
                
        # If no match found, return the original
        return field
    
    @classmethod
    def normalize_context(cls, context: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize all fields in a context dictionary to their canonical forms"""
        normalized = {}
        
        # First pass: collect all values under their canonical keys
        for key, value in context.items():
            canonical_key = cls.normalize_field(key)
            normalized[canonical_key] = value
            
        # Second pass: handle special cases and derived values
        # Example: if we have severity='high' but no animal_condition, set animal_condition='critical'
        if normalized.get(cls.SEVERITY.value) == 'high' and cls.ANIMAL_CONDITION.value not in normalized:
            normalized[cls.ANIMAL_CONDITION.value] = 'critical'
            
        return normalized
