from typing import List, Optional, Dict
from datetime import datetime, timedelta
import uuid

from .doctor import Doctor
from .patient import Patient
from .appointment import Appointment, AppointmentStatus, AppointmentType

class MockDatabase:
    """Mock database implementation for the health agent system"""
    
    def __init__(self):
        self.doctors: Dict[str, Doctor] = {}
        self.patients: Dict[str, Patient] = {}
        self.appointments: Dict[str, Appointment] = {}
        self._populate_sample_data()
    
    def _populate_sample_data(self):
        """Populate the database with sample data"""
        # Sample doctors
        sample_doctors = [
            Doctor(
                id="doc_001",
                name="Sarah Johnson",
                specialty="General Practice",
                email="s.johnson@healthcenter.com",
                phone="(555) 123-4567",
                available_days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                available_hours={"start": "09:00", "end": "17:00"}
            ),
            Doctor(
                id="doc_002",
                name="Michael Chen",
                specialty="Cardiology",
                email="m.chen@healthcenter.com",
                phone="(555) 234-5678",
                available_days=["Tuesday", "Wednesday", "Thursday"],
                available_hours={"start": "10:00", "end": "16:00"}
            ),
            Doctor(
                id="doc_003",
                name="Emily Rodriguez",
                specialty="Dermatology",
                email="e.rodriguez@healthcenter.com",
                phone="(555) 345-6789",
                available_days=["Monday", "Wednesday", "Friday"],
                available_hours={"start": "08:00", "end": "15:00"}
            ),
            Doctor(
                id="doc_004",
                name="David Kim",
                specialty="Pediatrics",
                email="d.kim@healthcenter.com",
                phone="(555) 456-7890",
                available_days=["Monday", "Tuesday", "Thursday", "Friday"],
                available_hours={"start": "09:30", "end": "17:30"}
            )
        ]
        
        for doctor in sample_doctors:
            self.doctors[doctor.id] = doctor
        
        # Sample patients
        sample_patients = [
            Patient(
                id="pat_001",
                name="John Smith",
                email="john.smith@email.com",
                phone="(555) 111-2222",
                date_of_birth="1985-03-15",
                insurance_provider="HealthPlus"
            ),
            Patient(
                id="pat_002",
                name="Maria Garcia",
                email="maria.garcia@email.com",
                phone="(555) 333-4444",
                date_of_birth="1992-07-22",
                insurance_provider="MediCare Pro"
            )
        ]
        
        for patient in sample_patients:
            self.patients[patient.id] = patient
    
    # Doctor operations
    def get_doctor(self, doctor_id: str) -> Optional[Doctor]:
        """Get a doctor by ID"""
        return self.doctors.get(doctor_id)
    
    def get_doctors_by_specialty(self, specialty: str) -> List[Doctor]:
        """Get all doctors with a specific specialty"""
        return [doc for doc in self.doctors.values() 
                if doc.specialty.lower() == specialty.lower() and doc.is_active]
    
    def get_all_doctors(self) -> List[Doctor]:
        """Get all active doctors"""
        return [doc for doc in self.doctors.values() if doc.is_active]
    
    def get_available_specialties(self) -> List[str]:
        """Get list of all available specialties"""
        return list(set(doc.specialty for doc in self.doctors.values() if doc.is_active))
    
    # Patient operations
    def get_patient(self, patient_id: str) -> Optional[Patient]:
        """Get a patient by ID"""
        return self.patients.get(patient_id)
    
    def find_patient_by_email(self, email: str) -> Optional[Patient]:
        """Find a patient by email"""
        for patient in self.patients.values():
            if patient.email and patient.email.lower() == email.lower():
                return patient
        return None
    
    def find_patient_by_phone(self, phone: str) -> Optional[Patient]:
        """Find a patient by phone number"""
        # Simple phone matching - in real system would normalize phone numbers
        for patient in self.patients.values():
            if patient.phone and patient.phone == phone:
                return patient
        return None
    
    def create_patient(self, name: str, email: str = None, phone: str = None, **kwargs) -> Patient:
        """Create a new patient"""
        patient_id = f"pat_{uuid.uuid4().hex[:8]}"
        patient = Patient(
            id=patient_id,
            name=name,
            email=email,
            phone=phone,
            **kwargs
        )
        self.patients[patient_id] = patient
        return patient
    
    # Appointment operations
    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        """Get an appointment by ID"""
        return self.appointments.get(appointment_id)
    
    def get_patient_appointments(self, patient_id: str) -> List[Appointment]:
        """Get all appointments for a patient"""
        return [apt for apt in self.appointments.values() if apt.patient_id == patient_id]
    
    def get_doctor_appointments(self, doctor_id: str, date: datetime = None) -> List[Appointment]:
        """Get appointments for a doctor, optionally filtered by date"""
        appointments = [apt for apt in self.appointments.values() if apt.doctor_id == doctor_id]
        
        if date:
            appointments = [apt for apt in appointments 
                          if apt.appointment_datetime.date() == date.date()]
        
        return sorted(appointments, key=lambda x: x.appointment_datetime)
    
    def check_doctor_availability(self, doctor_id: str, appointment_datetime: datetime, 
                                duration_minutes: int = 30) -> bool:
        """Check if a doctor is available at a specific time"""
        doctor = self.get_doctor(doctor_id)
        if not doctor or not doctor.is_active:
            return False
        
        # Check if doctor works on this day
        day_name = appointment_datetime.strftime("%A")
        if not doctor.is_available_on_day(day_name):
            return False
        
        # Check if time is within working hours
        if not doctor.is_available_at_time(appointment_datetime.time()):
            return False
        
        # Check for conflicts with existing appointments
        end_time = appointment_datetime + timedelta(minutes=duration_minutes)
        existing_appointments = self.get_doctor_appointments(doctor_id, appointment_datetime)
        
        for existing in existing_appointments:
            if existing.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]:
                existing_end = existing.get_end_datetime()
                # Check for overlap
                if not (end_time <= existing.appointment_datetime or 
                       existing_end <= appointment_datetime):
                    return False
        
        return True
    
    def create_appointment(self, patient_id: str, doctor_id: str, 
                         appointment_datetime: datetime, appointment_type: AppointmentType,
                         duration_minutes: int = 30, notes: str = None) -> Optional[Appointment]:
        """Create a new appointment"""
        # Validate availability
        if not self.check_doctor_availability(doctor_id, appointment_datetime, duration_minutes):
            return None
        
        appointment_id = f"apt_{uuid.uuid4().hex[:8]}"
        appointment = Appointment(
            id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_datetime=appointment_datetime,
            appointment_type=appointment_type,
            duration_minutes=duration_minutes,
            notes=notes
        )
        
        self.appointments[appointment_id] = appointment
        return appointment
    
    def get_available_slots(self, doctor_id: str, date: datetime, 
                          duration_minutes: int = 30) -> List[datetime]:
        """Get available time slots for a doctor on a specific date"""
        doctor = self.get_doctor(doctor_id)
        if not doctor:
            return []
        
        day_name = date.strftime("%A")
        if not doctor.is_available_on_day(day_name):
            return []
        
        # Parse working hours
        from datetime import time
        start_time = time.fromisoformat(doctor.available_hours['start'])
        end_time = time.fromisoformat(doctor.available_hours['end'])
        
        # Generate potential slots
        slots = []
        current_time = datetime.combine(date.date(), start_time)
        end_datetime = datetime.combine(date.date(), end_time)
        
        while current_time + timedelta(minutes=duration_minutes) <= end_datetime:
            if self.check_doctor_availability(doctor_id, current_time, duration_minutes):
                slots.append(current_time)
            current_time += timedelta(minutes=30)  # 30-minute intervals
        
        return slots
