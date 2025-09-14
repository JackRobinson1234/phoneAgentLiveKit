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
