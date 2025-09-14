from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, time

@dataclass
class Doctor:
    """Doctor model for the health agent system"""
    id: str
    name: str
    specialty: str
    email: str
    phone: str
    available_days: List[str]  # e.g., ['Monday', 'Tuesday', 'Wednesday']
    available_hours: dict  # e.g., {'start': '09:00', 'end': '17:00'}
    is_active: bool = True
    
    def __post_init__(self):
        """Validate doctor data after initialization"""
        if not self.id or not self.name:
            raise ValueError("Doctor ID and name are required")
        if not self.specialty:
            raise ValueError("Doctor specialty is required")
    
    def is_available_on_day(self, day_name: str) -> bool:
        """Check if doctor is available on a specific day"""
        return day_name in self.available_days and self.is_active
    
    def is_available_at_time(self, appointment_time: time) -> bool:
        """Check if doctor is available at a specific time"""
        start_time = time.fromisoformat(self.available_hours['start'])
        end_time = time.fromisoformat(self.available_hours['end'])
        return start_time <= appointment_time <= end_time
    
    def get_display_name(self) -> str:
        """Get formatted display name for the doctor"""
        return f"Dr. {self.name} ({self.specialty})"
