from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from enum import Enum

class AppointmentStatus(Enum):
    """Appointment status enumeration"""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class AppointmentType(Enum):
    """Appointment type enumeration"""
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    CHECKUP = "checkup"
    EMERGENCY = "emergency"
    VACCINATION = "vaccination"
    PROCEDURE = "procedure"

@dataclass
class Appointment:
    """Appointment model for the health agent system"""
    id: str
    patient_id: str
    doctor_id: str
    appointment_datetime: datetime
    appointment_type: AppointmentType
    duration_minutes: int = 30
    status: AppointmentStatus = AppointmentStatus.SCHEDULED
    notes: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        """Validate appointment data after initialization"""
        if not all([self.id, self.patient_id, self.doctor_id, self.appointment_datetime]):
            raise ValueError("Appointment ID, patient ID, doctor ID, and datetime are required")
        
        if self.duration_minutes <= 0:
            raise ValueError("Appointment duration must be positive")
            
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
    
    def is_upcoming(self) -> bool:
        """Check if appointment is in the future"""
        return self.appointment_datetime > datetime.now()
    
    def is_today(self) -> bool:
        """Check if appointment is today"""
        return self.appointment_datetime.date() == datetime.now().date()
    
    def get_formatted_datetime(self) -> str:
        """Get formatted appointment date and time"""
        return self.appointment_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
    
    def get_end_datetime(self) -> datetime:
        """Calculate appointment end time"""
        from datetime import timedelta
        return self.appointment_datetime + timedelta(minutes=self.duration_minutes)
    
    def conflicts_with(self, other_appointment: 'Appointment') -> bool:
        """Check if this appointment conflicts with another appointment"""
        if self.doctor_id != other_appointment.doctor_id:
            return False
            
        self_end = self.get_end_datetime()
        other_end = other_appointment.get_end_datetime()
        
        # Check for time overlap
        return not (self_end <= other_appointment.appointment_datetime or 
                   other_end <= self.appointment_datetime)
