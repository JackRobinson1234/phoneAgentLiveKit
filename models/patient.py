from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Patient:
    """Patient model for the health agent system"""
    id: str
    name: str
    email: str
    phone: str
    date_of_birth: Optional[str] = None
    insurance_provider: Optional[str] = None
    emergency_contact: Optional[str] = None
    medical_notes: Optional[str] = None
    created_at: datetime = None
    is_active: bool = True
    
    def __post_init__(self):
        """Validate patient data after initialization"""
        if not self.id or not self.name:
            raise ValueError("Patient ID and name are required")
        if not self.email and not self.phone:
            raise ValueError("At least one contact method (email or phone) is required")
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def get_display_name(self) -> str:
        """Get formatted display name for the patient"""
        return self.name
    
    def get_contact_info(self) -> str:
        """Get primary contact information"""
        if self.email:
            return self.email
        return self.phone
    
    def is_valid_for_booking(self) -> bool:
        """Check if patient has minimum required info for booking"""
        return bool(self.name and (self.email or self.phone) and self.is_active)
