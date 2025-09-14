from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import re

from .base_state import BaseState, StateResult
from models.appointment import AppointmentType
from models.database import MockDatabase

class GreetingState(BaseState):
    """Initial greeting state"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("GREETING")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        return "Hello! I'm HealthBot, your AI assistant for scheduling doctor appointments. How can I help you today?"
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        # Simple intent detection for appointment scheduling
        appointment_keywords = ['appointment', 'schedule', 'book', 'see doctor', 'visit']
        
        if any(keyword in user_input.lower() for keyword in appointment_keywords):
            context['intent'] = 'schedule_appointment'
            return StateResult.TRANSITION, "COLLECT_PATIENT_INFO", context
        
        # Handle other intents
        context['message'] = "I can help you schedule a doctor appointment. Would you like to book an appointment?"
        return StateResult.CONTINUE, None, context

class CollectPatientInfoState(BaseState):
    """Collect patient information"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("COLLECT_PATIENT_INFO")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        return "I'll help you schedule an appointment. First, I need some information. What's your name?"
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        if 'patient_name' not in context:
            # Extract name from input
            name = user_input.strip()
            if len(name) < 2:
                context['error_message'] = "Please provide a valid name."
                return StateResult.CONTINUE, None, context
            
            context['patient_name'] = name
            context['message'] = f"Thank you, {name}. What's your email address or phone number?"
            return StateResult.CONTINUE, None, context
        
        elif 'patient_contact' not in context:
            # Extract contact info
            contact = user_input.strip()
            
            # Simple validation for email or phone
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            phone_pattern = r'^\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})$'
            
            if re.match(email_pattern, contact):
                context['patient_contact'] = contact
                context['contact_type'] = 'email'
            elif re.match(phone_pattern, contact):
                context['patient_contact'] = contact
                context['contact_type'] = 'phone'
            else:
                context['error_message'] = "Please provide a valid email address or phone number."
                return StateResult.CONTINUE, None, context
            
            # Check if patient exists
            if context['contact_type'] == 'email':
                existing_patient = self.database.find_patient_by_email(contact)
            else:
                existing_patient = self.database.find_patient_by_phone(contact)
            
            if existing_patient:
                context['patient_id'] = existing_patient.id
                context['message'] = f"Welcome back, {existing_patient.name}!"
            else:
                # Create new patient
                patient_data = {'name': context['patient_name']}
                if context['contact_type'] == 'email':
                    patient_data['email'] = contact
                else:
                    patient_data['phone'] = contact
                
                new_patient = self.database.create_patient(**patient_data)
                context['patient_id'] = new_patient.id
                context['message'] = "Great! I've created your patient profile."
            
            return StateResult.TRANSITION, "COLLECT_APPOINTMENT_TYPE", context
        
        return StateResult.CONTINUE, None, context

class CollectAppointmentTypeState(BaseState):
    """Collect appointment type information"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("COLLECT_APPOINTMENT_TYPE")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        return ("What type of appointment do you need? You can choose from:\n"
                "1. Consultation\n"
                "2. Follow-up\n"
                "3. Checkup\n"
                "4. Vaccination\n"
                "5. Procedure\n"
                "Please type the number or name of the appointment type.")
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        user_input_lower = user_input.lower().strip()
        
        # Map input to appointment types
        type_mapping = {
            '1': AppointmentType.CONSULTATION,
            'consultation': AppointmentType.CONSULTATION,
            '2': AppointmentType.FOLLOW_UP,
            'follow-up': AppointmentType.FOLLOW_UP,
            'followup': AppointmentType.FOLLOW_UP,
            '3': AppointmentType.CHECKUP,
            'checkup': AppointmentType.CHECKUP,
            'check-up': AppointmentType.CHECKUP,
            '4': AppointmentType.VACCINATION,
            'vaccination': AppointmentType.VACCINATION,
            'vaccine': AppointmentType.VACCINATION,
            '5': AppointmentType.PROCEDURE,
            'procedure': AppointmentType.PROCEDURE
        }
        
        appointment_type = type_mapping.get(user_input_lower)
        if appointment_type:
            context['appointment_type'] = appointment_type
            return StateResult.TRANSITION, "COLLECT_DOCTOR_PREFERENCE", context
        
        context['error_message'] = "Please select a valid appointment type by number (1-5) or name."
        return StateResult.CONTINUE, None, context

class CollectDoctorPreferenceState(BaseState):
    """Collect doctor preference or specialty"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("COLLECT_DOCTOR_PREFERENCE")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        specialties = self.database.get_available_specialties()
        specialty_list = "\n".join([f"{i+1}. {spec}" for i, spec in enumerate(specialties)])
        
        return (f"Which doctor or specialty would you prefer?\n\n"
                f"Available specialties:\n{specialty_list}\n\n"
                f"You can choose by number, specialty name, or specific doctor name. "
                f"Or type 'any' for no preference.")
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        user_input_lower = user_input.lower().strip()
        
        if user_input_lower == 'any':
            context['doctor_preference'] = 'any'
            return StateResult.TRANSITION, "COLLECT_DATE_TIME", context
        
        # Check if it's a number (specialty selection)
        specialties = self.database.get_available_specialties()
        try:
            specialty_index = int(user_input) - 1
            if 0 <= specialty_index < len(specialties):
                context['preferred_specialty'] = specialties[specialty_index]
                return StateResult.TRANSITION, "COLLECT_DATE_TIME", context
        except ValueError:
            pass
        
        # Check if it matches a specialty name
        for specialty in specialties:
            if specialty.lower() in user_input_lower:
                context['preferred_specialty'] = specialty
                return StateResult.TRANSITION, "COLLECT_DATE_TIME", context
        
        # Check if it matches a doctor name
        doctors = self.database.get_all_doctors()
        for doctor in doctors:
            if doctor.name.lower() in user_input_lower:
                context['preferred_doctor_id'] = doctor.id
                return StateResult.TRANSITION, "COLLECT_DATE_TIME", context
        
        context['error_message'] = "Please select a valid specialty, doctor name, or type 'any'."
        return StateResult.CONTINUE, None, context

class CollectDateTimeState(BaseState):
    """Collect preferred date and time"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("COLLECT_DATE_TIME")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        return ("When would you like to schedule your appointment?\n"
                "Please provide a date and time (e.g., 'Monday at 2pm', 'December 15 at 10:30am', 'tomorrow morning').")
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        try:
            # Simple date/time parsing - in production would use more sophisticated NLP
            parsed_datetime = self._parse_datetime(user_input)
            if not parsed_datetime:
                context['error_message'] = "I couldn't understand that date/time. Please try again with a format like 'Monday at 2pm' or 'December 15 at 10:30am'."
                return StateResult.CONTINUE, None, context
            
            # Check if date is in the future
            if parsed_datetime <= datetime.now():
                context['error_message'] = "Please select a future date and time."
                return StateResult.CONTINUE, None, context
            
            context['preferred_datetime'] = parsed_datetime
            return StateResult.TRANSITION, "SHOW_AVAILABILITY", context
            
        except Exception as e:
            context['error_message'] = f"Error parsing date/time: {str(e)}. Please try again."
            return StateResult.CONTINUE, None, context
    
    def _parse_datetime(self, input_str: str) -> Optional[datetime]:
        """Simple datetime parsing - would use dateutil.parser in production"""
        from dateutil import parser
        
        try:
            # Handle relative dates
            input_lower = input_str.lower()
            now = datetime.now()
            
            if 'tomorrow' in input_lower:
                base_date = now + timedelta(days=1)
                # Extract time if provided
                time_match = re.search(r'(\d{1,2}):?(\d{0,2})\s*(am|pm)', input_lower)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0
                    if time_match.group(3) == 'pm' and hour != 12:
                        hour += 12
                    elif time_match.group(3) == 'am' and hour == 12:
                        hour = 0
                    return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    return base_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # Try to parse with dateutil
            return parser.parse(input_str, fuzzy=True)
            
        except:
            return None

class ShowAvailabilityState(BaseState):
    """Show available appointment slots"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("SHOW_AVAILABILITY")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        preferred_datetime = context['preferred_datetime']
        
        # Find suitable doctors
        suitable_doctors = self._find_suitable_doctors(context)
        
        if not suitable_doctors:
            return ("I'm sorry, but no doctors are available for your preferred specialty. "
                   "Would you like to try a different specialty or date?")
        
        # Find available slots
        available_slots = []
        for doctor in suitable_doctors:
            slots = self.database.get_available_slots(
                doctor.id, 
                preferred_datetime, 
                duration_minutes=30
            )
            for slot in slots[:3]:  # Show up to 3 slots per doctor
                available_slots.append((doctor, slot))
        
        if not available_slots:
            return ("I'm sorry, but there are no available slots for your preferred date and time. "
                   "Would you like to try a different date?")
        
        # Display available slots
        context['available_slots'] = available_slots
        message = "Here are the available appointment slots:\n\n"
        
        for i, (doctor, slot) in enumerate(available_slots[:5], 1):  # Show up to 5 options
            formatted_time = slot.strftime("%A, %B %d at %I:%M %p")
            message += f"{i}. Dr. {doctor.name} ({doctor.specialty}) - {formatted_time}\n"
        
        message += "\nPlease select an option by number, or type 'more' to see other dates."
        return message
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        user_input = user_input.strip().lower()
        
        if user_input == 'more':
            # Go back to collect different date/time
            return StateResult.TRANSITION, "COLLECT_DATE_TIME", context
        
        try:
            choice = int(user_input) - 1
            available_slots = context.get('available_slots', [])
            
            if 0 <= choice < len(available_slots):
                doctor, slot = available_slots[choice]
                context['selected_doctor'] = doctor
                context['selected_datetime'] = slot
                return StateResult.TRANSITION, "CONFIRM_APPOINTMENT", context
            else:
                context['error_message'] = "Please select a valid option number."
                return StateResult.CONTINUE, None, context
                
        except ValueError:
            context['error_message'] = "Please enter a number to select an appointment slot."
            return StateResult.CONTINUE, None, context
    
    def _find_suitable_doctors(self, context: Dict[str, Any]) -> list:
        """Find doctors based on user preferences"""
        if 'preferred_doctor_id' in context:
            doctor = self.database.get_doctor(context['preferred_doctor_id'])
            return [doctor] if doctor else []
        
        elif 'preferred_specialty' in context:
            return self.database.get_doctors_by_specialty(context['preferred_specialty'])
        
        else:
            return self.database.get_all_doctors()

class ConfirmAppointmentState(BaseState):
    """Confirm appointment details"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("CONFIRM_APPOINTMENT")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        doctor = context['selected_doctor']
        appointment_datetime = context['selected_datetime']
        appointment_type = context['appointment_type']
        
        formatted_time = appointment_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
        
        return (f"Please confirm your appointment details:\n\n"
                f"Doctor: Dr. {doctor.name} ({doctor.specialty})\n"
                f"Date & Time: {formatted_time}\n"
                f"Appointment Type: {appointment_type.value.title()}\n"
                f"Duration: 30 minutes\n\n"
                f"Type 'confirm' to book this appointment, or 'cancel' to start over.")
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        user_input = user_input.strip().lower()
        
        if user_input in ['confirm', 'yes', 'book']:
            # Create the appointment
            appointment = self.database.create_appointment(
                patient_id=context['patient_id'],
                doctor_id=context['selected_doctor'].id,
                appointment_datetime=context['selected_datetime'],
                appointment_type=context['appointment_type'],
                duration_minutes=30
            )
            
            if appointment:
                context['appointment_id'] = appointment.id
                return StateResult.TRANSITION, "BOOKING_COMPLETE", context
            else:
                context['error_message'] = "Sorry, there was an error booking your appointment. The slot may no longer be available."
                return StateResult.TRANSITION, "SHOW_AVAILABILITY", context
        
        elif user_input in ['cancel', 'no', 'back']:
            return StateResult.TRANSITION, "COLLECT_DATE_TIME", context
        
        else:
            context['error_message'] = "Please type 'confirm' to book the appointment or 'cancel' to go back."
            return StateResult.CONTINUE, None, context

class BookingCompleteState(BaseState):
    """Final state - booking complete"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("BOOKING_COMPLETE")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        appointment = self.database.get_appointment(context['appointment_id'])
        doctor = self.database.get_doctor(appointment.doctor_id)
        
        formatted_time = appointment.get_formatted_datetime()
        
        message = (f"✅ Your appointment has been successfully booked!\n\n"
                  f"Appointment Details:\n"
                  f"Doctor: Dr. {doctor.name} ({doctor.specialty})\n"
                  f"Date & Time: {formatted_time}\n"
                  f"Appointment ID: {appointment.id}\n\n"
                  f"You will receive a confirmation email/SMS shortly. "
                  f"Please arrive 15 minutes early for your appointment.\n\n"
                  f"Is there anything else I can help you with?")
        
        return message
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        user_input = user_input.strip().lower()
        
        if user_input in ['no', 'nothing', 'that\'s all', 'goodbye', 'bye']:
            context['completion_message'] = "Thank you for using HealthBot! Have a great day!"
            return StateResult.COMPLETE, None, context
        
        elif user_input in ['yes', 'help']:
            # Reset for new appointment
            keys_to_keep = ['patient_id', 'patient_name', 'patient_contact']
            new_context = {k: v for k, v in context.items() if k in keys_to_keep}
            return StateResult.TRANSITION, "COLLECT_APPOINTMENT_TYPE", new_context
        
        else:
            context['message'] = "I can help you book another appointment or answer questions. What would you like to do?"
            return StateResult.CONTINUE, None, context

class ErrorHandlingState(BaseState):
    """Handle errors and provide recovery options"""
    
    def __init__(self, database: MockDatabase):
        super().__init__("ERROR_HANDLING")
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        error_message = context.get('error_message', 'An unexpected error occurred.')
        
        return (f"{error_message}\n\n"
                f"Would you like to:\n"
                f"1. Start over\n"
                f"2. Try again\n"
                f"3. End conversation\n\n"
                f"Please select an option.")
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        user_input = user_input.strip().lower()
        
        if user_input in ['1', 'start over', 'restart']:
            # Clear context and start over
            new_context = {}
            return StateResult.TRANSITION, "GREETING", new_context
        
        elif user_input in ['2', 'try again', 'retry']:
            # Go back to previous state if possible
            previous_state = context.get('previous_state', 'GREETING')
            return StateResult.TRANSITION, previous_state, context
        
        elif user_input in ['3', 'end', 'quit', 'exit']:
            context['completion_message'] = "Thank you for using HealthBot. Goodbye!"
            return StateResult.COMPLETE, None, context
        
        else:
            context['error_message'] = "Please select option 1, 2, or 3."
            return StateResult.CONTINUE, None, context
