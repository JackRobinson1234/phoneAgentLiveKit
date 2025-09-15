from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import re

from .llm_state import LLMEnhancedState
from .base_state import StateResult
from models.appointment import AppointmentType
from models.database import MockDatabase

class LLMGreetingState(LLMEnhancedState):
    """LLM-enhanced greeting state"""
    
    def __init__(self, database: MockDatabase):
        system_prompt = """You are HealthBot, an AI assistant for scheduling doctor appointments.

Current State: GREETING - Initial interaction with the user

Your tasks:
1. First, analyze their input using analyze_appointment_request tool
2. Then, call generate_response tool with appropriate action

Decision logic:
- If user just says "hello" or greets: Respond warmly and ask what they need
- If user mentions ANY medical need (like "leg doctor", "knee hurts", "cardiologist"): 
  * Acknowledge their need
  * Use generate_response with next_action="transition" and next_state="COLLECT_PATIENT_INFO"
  * Say something like: "I'll help you with that. Let me get your information first. What's your name?"

CRITICAL: When user mentions a medical need, you MUST transition to COLLECT_PATIENT_INFO state."""
        
        super().__init__("GREETING", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        return "Hello! I'm HealthBot, your AI assistant for scheduling doctor appointments. How can I help you today?"
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        return self.process_input_with_llm(user_input, context)

class LLMCollectPatientInfoState(LLMEnhancedState):
    """LLM-enhanced patient information collection"""
    
    def __init__(self, database: MockDatabase):
        system_prompt = """You are HealthBot collecting patient information for appointment scheduling.

Current State: COLLECT_PATIENT_INFO - Gathering patient details

Your tasks:
1. Extract any patient info using extract_patient_info tool
2. Use generate_response tool with appropriate next steps

Decision logic:
- If no name collected yet: Ask for their name
- If name collected but no contact info: Ask for email or phone
- If both name and contact collected: Use next_action="transition" and next_state="COLLECT_APPOINTMENT_TYPE"

CRITICAL: Progress through the information collection systematically and transition when ready."""
        
        super().__init__("COLLECT_PATIENT_INFO", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        if context.get('extracted_name'):
            return f"Thank you! I have your name as {context['extracted_name']}. What's your email address or phone number?"
        return "I'll help you schedule an appointment. First, I need some information. What's your name?"
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Handle patient lookup and creation
        if updated_context.get('extracted_email') or updated_context.get('extracted_phone'):
            contact = updated_context.get('extracted_email') or updated_context.get('extracted_phone')
            contact_type = 'email' if '@' in contact else 'phone'
            
            # Check existing patient
            if contact_type == 'email':
                existing_patient = self.database.find_patient_by_email(contact)
            else:
                existing_patient = self.database.find_patient_by_phone(contact)
            
            if existing_patient:
                updated_context['patient_id'] = existing_patient.id
                updated_context['patient_name'] = existing_patient.name
                updated_context['welcome_back'] = True
            else:
                # Create new patient
                name = updated_context.get('extracted_name') or context.get('patient_name', 'Unknown')
                patient_data = {'name': name}
                if contact_type == 'email':
                    patient_data['email'] = contact
                else:
                    patient_data['phone'] = contact
                
                new_patient = self.database.create_patient(**patient_data)
                updated_context['patient_id'] = new_patient.id
                updated_context['patient_name'] = new_patient.name
                updated_context['new_patient'] = True
            
            # Auto-transition if we have complete info
            if updated_context.get('patient_id') and result == StateResult.CONTINUE:
                return StateResult.TRANSITION, "COLLECT_APPOINTMENT_TYPE", updated_context
        
        return result, next_state, updated_context

class LLMCollectAppointmentTypeState(LLMEnhancedState):
    """LLM-enhanced appointment type collection"""
    
    def __init__(self, database: MockDatabase):
        system_prompt = """You are HealthBot helping users select their appointment type.

Current State: COLLECT_APPOINTMENT_TYPE - Determining appointment type

Available appointment types:
- Consultation: Initial visit or new concern
- Follow-up: Return visit for ongoing care
- Checkup: Routine health examination
- Vaccination: Immunizations or shots
- Procedure: Medical procedures or treatments

Your tasks:
1. Present appointment type options clearly
2. Help user select appropriate type
3. Use analyze_appointment_request to understand their needs
4. Validate selection and proceed

Be helpful in explaining what each type involves if asked."""
        
        super().__init__("COLLECT_APPOINTMENT_TYPE", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        if context.get('welcome_back'):
            greeting = f"Welcome back, {context.get('patient_name', '')}!"
        elif context.get('new_patient'):
            greeting = "Great! I've created your patient profile."
        else:
            greeting = "Perfect!"
        
        return f"""{greeting} What type of appointment do you need?

1. Consultation - Initial visit or new concern
2. Follow-up - Return visit for ongoing care  
3. Checkup - Routine health examination
4. Vaccination - Immunizations or shots
5. Procedure - Medical procedures or treatments

You can tell me the number or describe what you need."""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Map suggested appointment type to enum
        if updated_context.get('suggested_appointment_type'):
            apt_type_map = {
                'consultation': AppointmentType.CONSULTATION,
                'follow-up': AppointmentType.FOLLOW_UP,
                'checkup': AppointmentType.CHECKUP,
                'vaccination': AppointmentType.VACCINATION,
                'procedure': AppointmentType.PROCEDURE
            }
            
            apt_type = apt_type_map.get(updated_context['suggested_appointment_type'])
            if apt_type:
                updated_context['appointment_type'] = apt_type
                if result == StateResult.CONTINUE:
                    return StateResult.TRANSITION, "COLLECT_DOCTOR_PREFERENCE", updated_context
        
        return result, next_state, updated_context

class LLMCollectDoctorPreferenceState(LLMEnhancedState):
    """LLM-enhanced doctor preference collection"""
    
    def __init__(self, database: MockDatabase):
        specialties = database.get_available_specialties()
        specialty_list = "\n".join([f"{i+1}. {spec}" for i, spec in enumerate(specialties)])
        
        system_prompt = f"""You are HealthBot helping users choose a doctor or specialty.

Current State: COLLECT_DOCTOR_PREFERENCE - Getting doctor/specialty preference

Available specialties:
{specialty_list}

Available doctors: {', '.join([f"Dr. {d.name} ({d.specialty})" for d in database.get_all_doctors()])}

Your tasks:
1. Present specialty and doctor options
2. Help user make selection
3. Handle "any" or "no preference" responses
4. Use analyze_appointment_request to understand preferences
5. Validate selection and proceed

Be flexible - users can choose by specialty, specific doctor, or say they have no preference."""
        
        super().__init__("COLLECT_DOCTOR_PREFERENCE", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        specialties = self.database.get_available_specialties()
        specialty_list = "\n".join([f"{i+1}. {spec}" for i, spec in enumerate(specialties)])
        
        return f"""Which doctor or specialty would you prefer?

Available specialties:
{specialty_list}

You can choose by number, specialty name, specific doctor name, or say 'any' for no preference."""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Handle specialty selection
        if updated_context.get('suggested_specialty'):
            specialty = updated_context['suggested_specialty']
            # Validate specialty exists
            available_specialties = self.database.get_available_specialties()
            if specialty in available_specialties:
                updated_context['preferred_specialty'] = specialty
                if result == StateResult.CONTINUE:
                    return StateResult.TRANSITION, "COLLECT_DATE_TIME", updated_context
        
        # Handle doctor selection
        if updated_context.get('suggested_doctor'):
            doctor_name = updated_context['suggested_doctor']
            doctors = self.database.get_all_doctors()
            for doctor in doctors:
                if doctor_name.lower() in doctor.name.lower():
                    updated_context['preferred_doctor_id'] = doctor.id
                    if result == StateResult.CONTINUE:
                        return StateResult.TRANSITION, "COLLECT_DATE_TIME", updated_context
                    break
        
        # Handle "any" preference
        user_lower = user_input.lower().strip()
        if any(phrase in user_lower for phrase in ['any', 'no preference', "don't care", 'whatever']):
            updated_context['doctor_preference'] = 'any'
            return StateResult.TRANSITION, "COLLECT_DATE_TIME", updated_context
        
        return result, next_state, updated_context

class LLMCollectDateTimeState(LLMEnhancedState):
    """LLM-enhanced date/time collection"""
    
    def __init__(self, database: MockDatabase):
        system_prompt = """You are HealthBot helping users schedule their appointment time.

Current State: COLLECT_DATE_TIME - Getting preferred date and time

Your tasks:
1. Ask for preferred date and time
2. Use parse_datetime_request to understand their input
3. Handle various formats (tomorrow at 2pm, Monday morning, Dec 15 at 10:30am)
4. Validate the date is in the future and during business hours
5. Provide helpful examples if they're unclear

Business hours are typically 9 AM to 5 PM, Monday through Friday.
Be flexible with date formats and help users understand what's possible."""
        
        super().__init__("COLLECT_DATE_TIME", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        return """When would you like to schedule your appointment?

You can say things like:
• "Tomorrow at 2pm"
• "Monday morning" 
• "December 15 at 10:30am"
• "Next week, any afternoon"

What works best for you?"""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Try to parse datetime from LLM output or fallback to simple parsing
        if updated_context.get('parsed_date') and updated_context.get('parsed_time'):
            try:
                date_str = updated_context['parsed_date']
                time_str = updated_context['parsed_time']
                datetime_str = f"{date_str} {time_str}"
                parsed_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
                
                # Validate future date
                if parsed_datetime > datetime.now():
                    updated_context['preferred_datetime'] = parsed_datetime
                    if result == StateResult.CONTINUE:
                        return StateResult.TRANSITION, "SHOW_AVAILABILITY", updated_context
                else:
                    updated_context['error_message'] = "Please select a future date and time."
                    return StateResult.CONTINUE, None, updated_context
                    
            except ValueError:
                pass
        
        # Fallback: simple relative parsing
        if not updated_context.get('preferred_datetime'):
            parsed_dt = self._simple_datetime_parse(user_input)
            if parsed_dt:
                updated_context['preferred_datetime'] = parsed_dt
                if result == StateResult.CONTINUE:
                    return StateResult.TRANSITION, "SHOW_AVAILABILITY", updated_context
        
        return result, next_state, updated_context
    
    def _simple_datetime_parse(self, input_str: str) -> Optional[datetime]:
        """Simple fallback datetime parsing"""
        from dateutil import parser
        try:
            return parser.parse(input_str, fuzzy=True)
        except:
            return None
class LLMShowAvailabilityState(LLMEnhancedState):
    """LLM-enhanced state for showing available appointment slots"""
    
    def __init__(self, database: MockDatabase):
        system_prompt = """You are HealthBot showing available appointment slots to users.

Current State: SHOW_AVAILABILITY - Displaying available slots and getting user selection

Your tasks:
1. Show the user available appointment slots based on their preferences
2. Help them select a slot or offer alternatives
3. Use the generate_response tool to provide your response

Available tools:
- generate_response: Provide your response and next action
- get_available_slots: Get available appointment slots based on context

When the user selects a slot, set next_action="transition" and next_state="CONFIRM_APPOINTMENT".
If they want more options, set next_action="transition" and next_state="COLLECT_DATE_TIME"."""
        
        super().__init__("SHOW_AVAILABILITY", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        preferred_datetime = context.get('preferred_datetime')
        if not preferred_datetime:
            return "I need to know your preferred date and time first. When would you like to schedule your appointment?"
            
        # Find suitable doctors
        suitable_doctors = self._find_suitable_doctors(context)
        
        if not suitable_doctors:
            return "I'm sorry, but no doctors are available for your preferred specialty. Would you like to try a different specialty or date?"
        
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
            return "I'm sorry, but there are no available slots for your preferred date and time. Would you like to try a different date?"
        
        # Store slots in context
        context['available_slots'] = available_slots
        
        # Display available slots
        message = "Here are the available appointment slots:\n\n"
        
        for i, (doctor, slot) in enumerate(available_slots[:5], 1):  # Show up to 5 options
            formatted_time = slot.strftime("%A, %B %d at %I:%M %p")
            message += f"{i}. Dr. {doctor.name} ({doctor.specialty}) - {formatted_time}\n"
        
        message += "\nPlease select an option by number, or type 'more' to see other dates."
        return message
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        return self.process_input_with_llm(user_input, context)
    
    def _find_suitable_doctors(self, context: Dict[str, Any]) -> list:
        """Find doctors based on user preferences"""
        if 'preferred_doctor_id' in context:
            doctor = self.database.get_doctor(context['preferred_doctor_id'])
            return [doctor] if doctor else []
        
        elif 'preferred_specialty' in context:
            return self.database.get_doctors_by_specialty(context['preferred_specialty'])
        
        else:
            return self.database.get_all_doctors()

class LLMConfirmAppointmentState(LLMEnhancedState):
    """LLM-enhanced state for confirming appointment details"""
    
    def __init__(self, database: MockDatabase):
        system_prompt = """You are HealthBot confirming appointment details with the user.

Current State: CONFIRM_APPOINTMENT - Getting final confirmation for booking

Your tasks:
1. Show the user their selected appointment details
2. Ask for confirmation to book the appointment
3. Use the generate_response tool to provide your response
4. Use the book_appointment tool when the user confirms

Available tools:
- generate_response: Provide your response and next action
- book_appointment: Book the appointment in the system

When the user confirms, use book_appointment tool, then set next_action="transition" and next_state="BOOKING_COMPLETE".
If they cancel, set next_action="transition" and next_state="COLLECT_DATE_TIME"."""
        
        super().__init__("CONFIRM_APPOINTMENT", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        doctor = context.get('selected_doctor')
        appointment_datetime = context.get('selected_datetime')
        appointment_type = context.get('appointment_type')
        
        if not doctor or not appointment_datetime or not appointment_type:
            return "I'm sorry, but I don't have all the necessary appointment details. Let's start over."
            
        formatted_time = appointment_datetime.strftime("%A, %B %d, %Y at %I:%M %p")
        
        return (f"Please confirm your appointment details:\n\n"
                f"Doctor: Dr. {doctor.name} ({doctor.specialty})\n"
                f"Date & Time: {formatted_time}\n"
                f"Appointment Type: {appointment_type.value.title()}\n"
                f"Duration: 30 minutes\n\n"
                f"Type 'confirm' to book this appointment, or 'cancel' to start over.")
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        return self.process_input_with_llm(user_input, context)
        
    def _handle_book_appointment(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment booking"""
        try:
            appointment = self.database.create_appointment(
                patient_id=context['patient_id'],
                doctor_id=context['selected_doctor'].id,
                appointment_datetime=context['selected_datetime'],
                appointment_type=context['appointment_type'],
                duration_minutes=30
            )
            
            if appointment:
                context['appointment_id'] = appointment.id
                return {
                    'success': True,
                    'appointment_id': appointment.id,
                    'message': 'Appointment booked successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to book appointment'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

class LLMBookingCompleteState(LLMEnhancedState):
    """LLM-enhanced state for booking completion"""
    
    def __init__(self, database: MockDatabase):
        system_prompt = """You are HealthBot confirming a successful appointment booking.

Current State: BOOKING_COMPLETE - Confirming successful booking and offering next steps

Your tasks:
1. Confirm the successful booking with appointment details
2. Offer additional assistance or conclude the conversation
3. Use the generate_response tool to provide your response

Available tools:
- generate_response: Provide your response and next action
- get_appointment_details: Get details about the booked appointment

When the user is done, set next_action="complete" to end the conversation.
If they want another appointment, set next_action="transition" and next_state="COLLECT_APPOINTMENT_TYPE".
"""
        
        super().__init__("BOOKING_COMPLETE", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        appointment_id = context.get('appointment_id')
        if not appointment_id:
            return "I'm sorry, but I don't have the appointment details. Would you like to schedule a new appointment?"
            
        appointment = self.database.get_appointment(appointment_id)
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
        return self.process_input_with_llm(user_input, context)
        
    def _handle_get_appointment_details(self, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Get appointment details"""
        try:
            appointment_id = context.get('appointment_id')
            if not appointment_id:
                return {
                    'success': False,
                    'error': 'No appointment ID in context'
                }
                
            appointment = self.database.get_appointment(appointment_id)
            if not appointment:
                return {
                    'success': False,
                    'error': 'Appointment not found'
                }
                
            doctor = self.database.get_doctor(appointment.doctor_id)
            
            return {
                'success': True,
                'appointment_id': appointment.id,
                'doctor_name': doctor.name,
                'doctor_specialty': doctor.specialty,
                'datetime': appointment.get_formatted_datetime(),
                'type': appointment.appointment_type.value
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

class LLMErrorHandlingState(LLMEnhancedState):
    """LLM-enhanced state for error handling"""
    
    def __init__(self, database: MockDatabase):
        system_prompt = """You are HealthBot helping users recover from errors.

Current State: ERROR_HANDLING - Helping the user recover from an error

Your tasks:
1. Acknowledge the error that occurred
2. Offer recovery options (start over, try again, or end conversation)
3. Use the generate_response tool to provide your response

Available tools:
- generate_response: Provide your response and next action

When the user wants to start over, set next_action="transition" and next_state="GREETING".
When the user wants to try again, set next_action="transition" and next_state equal to the previous_state in context.
When the user wants to end the conversation, set next_action="complete"."""
        
        super().__init__("ERROR_HANDLING", system_prompt)
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
        return self.process_input_with_llm(user_input, context)
