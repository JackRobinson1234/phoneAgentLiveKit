from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any


class CaseType(Enum):
    """Types of animal control cases"""
    EMERGENCY = "emergency"
    FOUND = "found"
    LOST = "lost"
    SURRENDER = "surrender"
    GENERAL = "general"


class CaseStatus(Enum):
    """Status of animal control cases"""
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Case:
    """Represents an animal control case"""
    
    def __init__(self, 
                 id: str,
                 case_type: CaseType,
                 animal_type: str,
                 location: str,
                 reporter_name: Optional[str] = None,
                 reporter_contact: Optional[str] = None,
                 description: Optional[str] = None,
                 status: CaseStatus = CaseStatus.SUBMITTED,
                 details: Optional[Dict[str, Any]] = None):
        self.id = id
        self.case_type = case_type
        self.animal_type = animal_type
        self.location = location
        self.reporter_name = reporter_name
        self.reporter_contact = reporter_contact
        self.description = description
        self.status = status
        self.details = details or {}
        self.created_at = datetime.now()
        self.updated_at = self.created_at
    
    def update_status(self, status: CaseStatus) -> None:
        """Update the case status"""
        self.status = status
        self.updated_at = datetime.now()
    
    def add_details(self, key: str, value: Any) -> None:
        """Add additional details to the case"""
        self.details[key] = value
        self.updated_at = datetime.now()
    
    def get_formatted_creation_time(self) -> str:
        """Get a formatted string of the creation time"""
        return self.created_at.strftime("%A, %B %d, %Y at %I:%M %p")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert case to dictionary representation"""
        return {
            "id": self.id,
            "case_type": self.case_type.value,
            "animal_type": self.animal_type,
            "location": self.location,
            "reporter_name": self.reporter_name,
            "reporter_contact": self.reporter_contact,
            "description": self.description,
            "status": self.status.value,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
