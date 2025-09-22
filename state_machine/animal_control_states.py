from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import re

from .animal_control_state import AnimalControlState, StateResult
from models.animal_database import MockAnimalDatabase
from models.case import Case, CaseType, CaseStatus

class LLMGreetingAndDetermineServiceState(AnimalControlState):
    """Combined LLM-enhanced greeting and service determination state"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot, an AI assistant for animal control services.

Current State: GREETING - Initial interaction with the user and service determination

Available services:
1. Injured, Abused, or Emergency Cases
2. Report Found Animal
3. Report Lost Animal
4. Schedule Pet Surrender
5. General Information

Your tasks:
1. First, analyze their input using analyze_request tool
2. Then, call generate_response tool with appropriate action

Decision logic:
- If user just says "hello" or greets: Respond warmly and present the available services
- If user mentions injured/sick/abused animal or emergency: transition to "EMERGENCY_CASE"
- If user wants to report a found animal: transition to "REPORT_FOUND"
- If user wants to report a lost animal: transition to "REPORT_LOST"
- If user wants to surrender a pet: transition to "PET_SURRENDER"
- If user needs general information: transition to "GENERAL_INFO"
- If unclear: Ask clarifying questions and present the available services

CRITICAL: Determine the correct service and transition to the appropriate state when possible."""
        
        super().__init__("GREETING", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        return """Hello! I'm AnimalControlBot, your AI assistant for animal control services.

I can help you with the following services:

1. Injured, Abused, or Emergency Cases
2. Report Found Animal
3. Report Lost Animal
4. Schedule Pet Surrender
5. General Information

How can I assist you today? You can select a number or describe your situation."""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Handle service selection from numeric input
        try:
            selection = int(user_input.strip())
            if 1 <= selection <= 5:
                service_map = {
                    1: "EMERGENCY_CASE",
                    2: "REPORT_FOUND",
                    3: "REPORT_LOST",
                    4: "PET_SURRENDER",
                    5: "GENERAL_INFO"
                }
                return StateResult.TRANSITION, service_map[selection], updated_context
        except ValueError:
            pass
        
        return result, next_state, updated_context

class LLMEmergencyCaseState(AnimalControlState):
    """LLM-enhanced emergency case handling state with step-by-step information collection"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot handling emergency animal cases.

Current State: EMERGENCY_CASE - Collecting information about an injured, abused, or emergency animal case

Your tasks:
1. Collect information ONE STEP AT A TIME in this order:
   a. Animal type (dog, cat, bird, etc.)
   b. The animal's condition or situation (injured, sick, abused)
   c. Location of the animal (address or landmarks)
   d. Whether the animal is contained/secured or loose

2. For each step:
   - Ask for ONLY the next missing piece of information
   - If user provides multiple pieces of information at once, acknowledge and extract all provided info
   - Don't repeat questions for information already provided
   - Move to the next missing information

3. Provide immediate guidance based on the situation
4. Use generate_response with appropriate next_action

CRITICAL: For true emergencies, emphasize the importance of calling the emergency hotline immediately.
CRITICAL: Collect information ONE STEP AT A TIME, but be flexible to accept multiple pieces of information when provided."""
        
        super().__init__("EMERGENCY_CASE", system_prompt)
        self.database = database
        self.required_fields = [
            'animal_type',        # Step 1a
            'animal_condition',  # Step 1b
            'location',          # Step 1c
            'animal_contained'   # Step 1d
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        return """I understand this is an emergency animal situation. Let's gather the necessary information quickly.

First, what type of animal is involved?"""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Determine which information we still need to collect
        missing_fields = self._get_missing_fields(updated_context)
        
        # If we have all required information, prepare to transition
        if not missing_fields:
            # Create case details from collected information
            updated_context['case_details'] = {
                'type': 'emergency',
                'animal_type': updated_context.get('animal_type'),
                'condition': updated_context.get('animal_condition', 'Unknown'),
                'location': updated_context.get('location'),
                'contained': updated_context.get('animal_contained', 'Unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Add a message to the context indicating all information has been collected
            updated_context['message'] = "Thank you for providing all the necessary information about this emergency case. Let me summarize what we have so far."
            
            # For emergencies, always remind about the hotline
            if 'critical' in updated_context.get('animal_condition', '').lower() or 'severe' in updated_context.get('animal_condition', '').lower():
                updated_context['message'] += "\n\nThis appears to be a critical emergency. Please call our emergency hotline at 555-ANIMAL immediately."
            
            return StateResult.TRANSITION, "CASE_CONFIRMATION", updated_context
        
        # Otherwise, ask for the next piece of information
        next_field = missing_fields[0]
        prompt_message = self._get_prompt_for_field(next_field, updated_context)
        
        # Only override the message if the LLM didn't provide a good follow-up question
        if not updated_context.get('message') or 'thank you' in updated_context.get('message', '').lower():
            updated_context['message'] = prompt_message
        
        return StateResult.CONTINUE, None, updated_context
    
    def _get_missing_fields(self, context: Dict[str, Any]) -> list:
        """Determine which required fields are still missing"""
        return [field for field in self.required_fields if not context.get(field)]
    
    def _get_prompt_for_field(self, field: str, context: Dict[str, Any]) -> str:
        """Get the appropriate prompt for the next required field"""
        prompts = {
            'animal_type': "What type of animal is involved in this emergency?",
            'animal_condition': "What is the animal's condition or situation? (injured, sick, abused, etc.)",
            'location': "Where is the animal located? Please provide an address or landmarks.",
            'animal_contained': "Is the animal contained/secured or is it loose?"
        }
        
        # Acknowledge information already provided
        acknowledgment = ""
        if context.get('animal_type'):
            acknowledgment += f"I understand this emergency involves a {context.get('animal_type')}. "
        if context.get('animal_condition'):
            acknowledgment += f"The animal is {context.get('animal_condition')}. "
        
        # Add emergency hotline reminder for all prompts
        emergency_note = "\n\nFor immediate assistance with critically injured animals, please call our emergency hotline at 555-ANIMAL."
        
        if acknowledgment:
            return f"{acknowledgment}\n\n{prompts[field]}{emergency_note}"
        else:
            return f"{prompts[field]}{emergency_note}"

class LLMReportFoundState(AnimalControlState):
    """LLM-enhanced state for reporting found animals with step-by-step information collection"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot helping users report found animals.

Current State: REPORT_FOUND - Collecting information about a found animal

Your tasks:
1. Collect information ONE STEP AT A TIME in this order:
   a. Animal type (dog, cat, bird, etc.) and breed if known
   b. Color, size, and appearance
   c. Where and when the animal was found
   d. Identifying features (collar, tags, microchip, distinctive markings)
   e. Whether the finder can temporarily keep the animal

2. For each step:
   - Ask for ONLY the next missing piece of information
   - If user provides multiple pieces of information at once, acknowledge and extract all provided info
   - Don't repeat questions for information already provided
   - Move to the next missing information

3. Use generate_response with appropriate next_action

CRITICAL: Collect information ONE STEP AT A TIME, but be flexible to accept multiple pieces of information when provided."""
        
        super().__init__("REPORT_FOUND", system_prompt)
        self.database = database
        self.required_fields = [
            'animal_type',        # Step 1a
            'animal_description', # Step 1b
            'location_found',    # Step 1c
            'identifying_features', # Step 1d
            'finder_can_keep'    # Step 1e
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        return """Thank you for reporting a found animal. Let's start gathering information to help reunite it with its owner.

First, please tell me what type of animal you've found (dog, cat, bird, etc.) and the breed if you know it."""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Determine which information we still need to collect
        missing_fields = self._get_missing_fields(updated_context)
        
        # If we have all required information, prepare to transition
        if not missing_fields:
            # Create case details from collected information
            updated_context['case_details'] = {
                'type': 'found',
                'animal_type': updated_context.get('animal_type'),
                'description': updated_context.get('animal_description', ''),
                'location_found': updated_context.get('location_found'),
                'found_time': updated_context.get('found_time', 'Recently'),
                'identifying_features': updated_context.get('identifying_features', 'None reported'),
                'finder_can_keep': updated_context.get('finder_can_keep', False),
                'finder_contact': updated_context.get('finder_contact', ''),
                'timestamp': datetime.now().isoformat()
            }
            
            # Add a message to the context indicating all information has been collected
            updated_context['message'] = "Thank you for providing all the necessary information about the found animal. Let me summarize what we have so far."
            
            return StateResult.TRANSITION, "CASE_CONFIRMATION", updated_context
        
        # Otherwise, ask for the next piece of information
        next_field = missing_fields[0]
        prompt_message = self._get_prompt_for_field(next_field, updated_context)
        
        # Only override the message if the LLM didn't provide a good follow-up question
        if not updated_context.get('message') or 'thank you' in updated_context.get('message', '').lower():
            updated_context['message'] = prompt_message
        
        return StateResult.CONTINUE, None, updated_context
    
    def _get_missing_fields(self, context: Dict[str, Any]) -> list:
        """Determine which required fields are still missing"""
        return [field for field in self.required_fields if not context.get(field)]
    
    def _get_prompt_for_field(self, field: str, context: Dict[str, Any]) -> str:
        """Get the appropriate prompt for the next required field"""
        prompts = {
            'animal_type': "What type of animal have you found (dog, cat, bird, etc.)? Please include the breed if you know it.",
            'animal_description': "Thank you. Now, could you describe the animal's color, size, and general appearance?",
            'location_found': "Where and when did you find the animal?",
            'identifying_features': "Does the animal have any identifying features like a collar, tags, or distinctive markings?",
            'finder_can_keep': "Are you able to temporarily keep the animal while we search for its owner? If not, we can arrange pickup."
        }
        
        # Acknowledge information already provided
        acknowledgment = ""
        if context.get('animal_type'):
            acknowledgment += f"I have that you found a {context.get('animal_type')}. "
        
        if acknowledgment:
            return f"{acknowledgment}\n\n{prompts[field]}"
        else:
            return prompts[field]

class LLMReportLostState(AnimalControlState):
    """LLM-enhanced state for reporting lost animals with step-by-step information collection"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot helping users report lost animals.

Current State: REPORT_LOST - Collecting information about a lost animal

Your tasks:
1. Collect information ONE STEP AT A TIME in this order:
   a. Animal type (dog, cat, bird, etc.), breed, and name
   b. Color, size, and any distinctive markings
   c. Where and when the animal was last seen
   d. Identifying features (collar, tags, microchip)
   e. Owner contact information (name and phone number)

2. For each step:
   - Ask for ONLY the next missing piece of information
   - If user provides multiple pieces of information at once, acknowledge and extract all provided info
   - Don't repeat questions for information already provided
   - Move to the next missing information

3. Use generate_response with appropriate next_action

CRITICAL: Collect information ONE STEP AT A TIME, but be flexible to accept multiple pieces of information when provided."""
        
        super().__init__("REPORT_LOST", system_prompt)
        self.database = database
        self.required_fields = [
            'animal_type',        # Step 1a
            'animal_description', # Step 1b
            'last_seen_location', # Step 1c
            'identifying_features', # Step 1d
            'owner_contact'       # Step 1e
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        return """I'm sorry to hear about your lost pet. Let's start gathering information to help find them.

First, please tell me what type of animal you've lost (dog, cat, bird, etc.), including breed and name if you know them."""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Determine which information we still need to collect
        missing_fields = self._get_missing_fields(updated_context)
        
        # If we have all required information, prepare to transition
        if not missing_fields:
            # Create case details from collected information
            updated_context['case_details'] = {
                'type': 'lost',
                'animal_type': updated_context.get('animal_type'),
                'animal_name': updated_context.get('animal_name', 'Unknown'),
                'description': updated_context.get('animal_description', ''),
                'last_seen_location': updated_context.get('last_seen_location'),
                'last_seen_time': updated_context.get('last_seen_time', 'Recently'),
                'identifying_features': updated_context.get('identifying_features', 'None reported'),
                'owner_name': updated_context.get('owner_name', ''),
                'owner_contact': updated_context.get('owner_contact', ''),
                'timestamp': datetime.now().isoformat()
            }
            
            # Add a message to the context indicating all information has been collected
            updated_context['message'] = "Thank you for providing all the necessary information about your lost pet. Let me summarize what we have so far."
            
            return StateResult.TRANSITION, "CASE_CONFIRMATION", updated_context
        
        # Otherwise, ask for the next piece of information
        next_field = missing_fields[0]
        prompt_message = self._get_prompt_for_field(next_field, updated_context)
        
        # Only override the message if the LLM didn't provide a good follow-up question
        if not updated_context.get('message') or 'thank you' in updated_context.get('message', '').lower():
            updated_context['message'] = prompt_message
        
        return StateResult.CONTINUE, None, updated_context
    
    def _get_missing_fields(self, context: Dict[str, Any]) -> list:
        """Determine which required fields are still missing"""
        return [field for field in self.required_fields if not context.get(field)]
    
    def _get_prompt_for_field(self, field: str, context: Dict[str, Any]) -> str:
        """Get the appropriate prompt for the next required field"""
        prompts = {
            'animal_type': "What type of animal have you lost (dog, cat, bird, etc.)? Please include the breed and name if you know them.",
            'animal_description': "Thank you. Now, could you describe your pet's color, size, and any distinctive markings?",
            'last_seen_location': "Where and when was your pet last seen?",
            'identifying_features': "Is your pet wearing a collar, tags, or are they microchipped? Any other identifying features?",
            'owner_contact': "Finally, please provide your contact information (name and phone number) so we can reach you if your pet is found."
        }
        
        # Acknowledge information already provided
        acknowledgment = ""
        if context.get('animal_type'):
            acknowledgment += f"I have that your lost pet is a {context.get('animal_type')}. "
        if context.get('animal_name'):
            acknowledgment += f"Their name is {context.get('animal_name')}. "
        
        if acknowledgment:
            return f"{acknowledgment}\n\n{prompts[field]}"
        else:
            return prompts[field]

class LLMPetSurrenderState(AnimalControlState):
    """LLM-enhanced state for pet surrender scheduling with step-by-step information collection"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot helping users schedule pet surrenders.

Current State: PET_SURRENDER - Collecting information for pet surrender

Your tasks:
1. Collect information ONE STEP AT A TIME in this order:
   a. Animal type (dog, cat, etc.), breed, age, and name
   b. Reason for surrender
   c. Medical or behavioral issues
   d. Owner contact information (name and phone number)

2. For each step:
   - Ask for ONLY the next missing piece of information
   - If user provides multiple pieces of information at once, acknowledge and extract all provided info
   - Don't repeat questions for information already provided
   - Move to the next missing information

3. Use generate_response with appropriate next_action

CRITICAL: Be compassionate but informative about the surrender process.
CRITICAL: Collect information ONE STEP AT A TIME, but be flexible to accept multiple pieces of information when provided."""
        
        super().__init__("PET_SURRENDER", system_prompt)
        self.database = database
        self.required_fields = [
            'animal_type',        # Step 1a
            'surrender_reason',  # Step 1b
            'health_issues',     # Step 1c (combines medical and behavioral)
            'owner_contact'      # Step 1d
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        return """I understand you're considering surrendering a pet. This can be a difficult decision.

Let's start gathering the information we need. First, could you tell me what type of animal you're surrendering (dog, cat, etc.), including breed, age, and name if you know them?"""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Determine which information we still need to collect
        missing_fields = self._get_missing_fields(updated_context)
        
        # If we have all required information, prepare to transition
        if not missing_fields:
            # Create case details from collected information
            updated_context['case_details'] = {
                'type': 'surrender',
                'animal_type': updated_context.get('animal_type'),
                'animal_name': updated_context.get('animal_name', 'Unknown'),
                'animal_age': updated_context.get('animal_age', 'Unknown'),
                'surrender_reason': updated_context.get('surrender_reason', ''),
                'medical_issues': updated_context.get('medical_issues', 'None reported'),
                'behavioral_issues': updated_context.get('behavioral_issues', 'None reported'),
                'owner_name': updated_context.get('owner_name', ''),
                'owner_contact': updated_context.get('owner_contact', ''),
                'timestamp': datetime.now().isoformat()
            }
            
            # Add a message to the context indicating all information has been collected
            updated_context['message'] = "Thank you for providing all the necessary information about your pet surrender request. Let's schedule an appointment for the surrender."
            
            return StateResult.TRANSITION, "SCHEDULE_SURRENDER", updated_context
        
        # Otherwise, ask for the next piece of information
        next_field = missing_fields[0]
        prompt_message = self._get_prompt_for_field(next_field, updated_context)
        
        # Only override the message if the LLM didn't provide a good follow-up question
        if not updated_context.get('message') or 'thank you' in updated_context.get('message', '').lower():
            updated_context['message'] = prompt_message
        
        return StateResult.CONTINUE, None, updated_context
    
    def _get_missing_fields(self, context: Dict[str, Any]) -> list:
        """Determine which required fields are still missing"""
        return [field for field in self.required_fields if not context.get(field)]
    
    def _get_prompt_for_field(self, field: str, context: Dict[str, Any]) -> str:
        """Get the appropriate prompt for the next required field"""
        prompts = {
            'animal_type': "What type of animal are you surrendering (dog, cat, etc.)? Please include breed, age, and name if you know them.",
            'surrender_reason': "I understand this can be difficult. Could you share the reason you need to surrender your pet?",
            'health_issues': "Are there any medical or behavioral issues we should be aware of?",
            'owner_contact': "Finally, please provide your contact information (name and phone number) so we can reach you to schedule the surrender."
        }
        
        # Acknowledge information already provided
        acknowledgment = ""
        if context.get('animal_type'):
            pet_type = context.get('animal_type')
            pet_name = context.get('animal_name', '')
            if pet_name:
                acknowledgment += f"I understand you're surrendering your {pet_type} named {pet_name}. "
            else:
                acknowledgment += f"I understand you're surrendering your {pet_type}. "
        
        if acknowledgment:
            return f"{acknowledgment}\n\n{prompts[field]}"
        else:
            return prompts[field]

class LLMScheduleSurrenderState(AnimalControlState):
    """LLM-enhanced state for scheduling pet surrender appointments"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot scheduling pet surrender appointments.

Current State: SCHEDULE_SURRENDER - Scheduling a surrender appointment

Your tasks:
1. Present available dates and times for surrender appointments
2. Help user select a convenient time
3. Confirm the appointment details
4. Use generate_response with appropriate next_action

CRITICAL: Ensure the user understands the surrender process and what to bring."""
        
        super().__init__("SCHEDULE_SURRENDER", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        # In a real system, these would come from a database
        available_dates = [
            "Monday, October 5 (10:00 AM - 2:00 PM)",
            "Wednesday, October 7 (1:00 PM - 4:00 PM)",
            "Friday, October 9 (9:00 AM - 12:00 PM)"
        ]
        
        dates_list = "\n".join([f"{i+1}. {date}" for i, date in enumerate(available_dates)])
        
        return f"""Thank you for providing that information. We can schedule your pet surrender appointment on one of the following dates:

{dates_list}

Please select a date by number, or let me know if none of these work for you.

On the day of surrender, please bring:
- Your photo ID
- Any medical records for the pet
- Any supplies or favorite toys you wish to donate with the pet"""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Handle date selection
        try:
            selection = int(user_input.strip())
            if 1 <= selection <= 3:
                available_dates = [
                    "Monday, October 5 (10:00 AM - 2:00 PM)",
                    "Wednesday, October 7 (1:00 PM - 4:00 PM)",
                    "Friday, October 9 (9:00 AM - 12:00 PM)"
                ]
                updated_context['selected_date'] = available_dates[selection-1]
                updated_context['case_details']['appointment_date'] = available_dates[selection-1]
                
                if result == StateResult.CONTINUE:
                    return StateResult.TRANSITION, "CASE_CONFIRMATION", updated_context
        except ValueError:
            pass
        
        return result, next_state, updated_context

class LLMGeneralInfoState(AnimalControlState):
    """LLM-enhanced state for providing general information"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot providing general information about animal control services.

Current State: GENERAL_INFO - Providing general information about services

Your tasks:
1. Answer general questions about animal control services
2. Provide information about adoption, licensing, wildlife, etc.
3. Direct users to specific services if needed
4. Use generate_response with appropriate next_action

CRITICAL: Be informative and helpful, directing users to specific services when appropriate."""
        
        super().__init__("GENERAL_INFO", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        return """I can provide information about our animal control services, including:

- Animal adoption process
- Pet licensing requirements
- Wildlife management
- Spay/neuter programs
- Animal noise or nuisance complaints
- Volunteer opportunities

What specific information are you looking for today?"""
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # If the user's query matches a specific service, transition to that service
        user_input_lower = user_input.lower()
        
        if any(term in user_input_lower for term in ['injured', 'hurt', 'emergency', 'abuse']):
            return StateResult.TRANSITION, "EMERGENCY_CASE", updated_context
        elif any(term in user_input_lower for term in ['found', 'stray']):
            return StateResult.TRANSITION, "REPORT_FOUND", updated_context
        elif any(term in user_input_lower for term in ['lost', 'missing']):
            return StateResult.TRANSITION, "REPORT_LOST", updated_context
        elif any(term in user_input_lower for term in ['surrender', 'give up', 'rehome']):
            return StateResult.TRANSITION, "PET_SURRENDER", updated_context
        
        return result, next_state, updated_context

class LLMCaseConfirmationState(AnimalControlState):
    """LLM-enhanced state for case confirmation"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot confirming case details with the user.

Current State: CASE_CONFIRMATION - Confirming case details and providing next steps

Your tasks:
1. Summarize the collected information
2. Confirm details with the user
3. Provide appropriate next steps based on the case type
4. Use generate_response with appropriate next_action

CRITICAL: Ensure all necessary information has been collected and provide clear next steps."""
        
        super().__init__("CASE_CONFIRMATION", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        case_details = context.get('case_details', {})
        case_type = case_details.get('type', 'unknown')
        
        if case_type == 'emergency':
            summary = f"""Thank you for reporting this emergency case. Here's what I've recorded:

- Animal type: {case_details.get('animal_type', 'Unknown')}
- Condition: {case_details.get('condition', 'Unknown')}
- Location: {case_details.get('location', 'Unknown')}
- Contained/Secured: {case_details.get('contained', 'Unknown')}

For immediate assistance, please call our emergency hotline at 555-ANIMAL.
An animal control officer will be dispatched to the location as soon as possible.

Is this information correct? If not, please let me know what needs to be changed."""

        elif case_type == 'found':
            summary = f"""Thank you for reporting this found animal. Here's what I've recorded:

- Animal type: {case_details.get('animal_type', 'Unknown')}
- Description: {case_details.get('description', 'Unknown')}
- Location found: {case_details.get('location_found', 'Unknown')}
- When found: {case_details.get('found_time', 'Unknown')}
- Identifying features: {case_details.get('identifying_features', 'None reported')}
- Can keep temporarily: {'Yes' if case_details.get('finder_can_keep') else 'No'}

We'll check our lost pet reports for potential matches. An officer will contact you within 24 hours.

Is this information correct? If not, please let me know what needs to be changed."""

        elif case_type == 'lost':
            summary = f"""I'm sorry about your lost pet. Here's what I've recorded:

- Animal type: {case_details.get('animal_type', 'Unknown')}
- Name: {case_details.get('animal_name', 'Unknown')}
- Description: {case_details.get('description', 'Unknown')}
- Last seen location: {case_details.get('last_seen_location', 'Unknown')}
- Last seen time: {case_details.get('last_seen_time', 'Unknown')}
- Identifying features: {case_details.get('identifying_features', 'None reported')}
- Owner: {case_details.get('owner_name', 'Unknown')}
- Contact: {case_details.get('owner_contact', 'Unknown')}

We'll check our found animal reports and alert our field officers. We'll contact you if we find a match.

Is this information correct? If not, please let me know what needs to be changed."""

        elif case_type == 'surrender':
            summary = f"""Thank you for providing information about your pet surrender. Here's what I've recorded:

- Animal type: {case_details.get('animal_type', 'Unknown')}
- Name: {case_details.get('animal_name', 'Unknown')}
- Age: {case_details.get('animal_age', 'Unknown')}
- Reason for surrender: {case_details.get('surrender_reason', 'Unknown')}
- Medical issues: {case_details.get('medical_issues', 'None reported')}
- Behavioral issues: {case_details.get('behavioral_issues', 'None reported')}
- Owner: {case_details.get('owner_name', 'Unknown')}
- Contact: {case_details.get('owner_contact', 'Unknown')}
- Appointment: {case_details.get('appointment_date', 'Not scheduled yet')}

Is this information correct? If not, please let me know what needs to be changed."""

        else:
            summary = """Thank you for providing this information. Please confirm that the details are correct, or let me know what needs to be changed."""
            
        return summary
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Check for confirmation
        user_input_lower = user_input.lower()
        if any(term in user_input_lower for term in ['yes', 'correct', 'right', 'good', 'confirm']):
            # Generate case ID
            case_id = f"CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            updated_context['case_id'] = case_id
            updated_context['case_details']['case_id'] = case_id
            updated_context['case_details']['status'] = 'submitted'
            
            # In a real system, we would save the case to a database here
            
            return StateResult.TRANSITION, "CASE_COMPLETE", updated_context
        
        return result, next_state, updated_context

class LLMCaseCompleteState(AnimalControlState):
    """LLM-enhanced state for case completion"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot confirming case submission and providing final information.

Current State: CASE_COMPLETE - Confirming case submission and providing next steps

Your tasks:
1. Confirm the case has been submitted
2. Provide the case ID for reference
3. Explain what happens next
4. Ask if there's anything else the user needs
5. Use generate_response with appropriate next_action

CRITICAL: Ensure the user knows their case has been submitted and what to expect next."""
        
        super().__init__("CASE_COMPLETE", system_prompt)
        self.database = database
    
    def enter(self, context: Dict[str, Any]) -> str:
        case_details = context.get('case_details', {})
        case_type = case_details.get('type', 'unknown')
        case_id = context.get('case_id', 'UNKNOWN-ID')
        
        if case_type == 'emergency':
            message = f"""✅ Your emergency animal case has been submitted successfully!

Case ID: {case_id}

What happens next:
- An animal control officer will be dispatched to the location
- For immediate assistance, please call our emergency hotline at 555-ANIMAL
- You may receive a follow-up call for additional information

Thank you for reporting this emergency. Is there anything else I can help you with today?"""

        elif case_type == 'found':
            message = f"""✅ Your found animal report has been submitted successfully!

Case ID: {case_id}

What happens next:
- We'll check our lost pet reports for potential matches
- An officer will contact you within 24 hours
- If you can keep the animal temporarily, we'll provide guidance on care

Thank you for helping this animal. Is there anything else I can help you with today?"""

        elif case_type == 'lost':
            message = f"""✅ Your lost pet report has been submitted successfully!

Case ID: {case_id}

What happens next:
- We'll check our found animal reports for potential matches
- Our field officers will be alerted to look for your pet
- We recommend posting on local lost pet websites and social media
- We'll contact you if we find a potential match

We hope your pet returns home soon. Is there anything else I can help you with today?"""

        elif case_type == 'surrender':
            appointment_date = case_details.get('appointment_date', 'Not scheduled')
            message = f"""✅ Your pet surrender appointment has been confirmed!

Case ID: {case_id}
Appointment: {appointment_date}

What to bring:
- Your photo ID
- Any medical records for the pet
- Any supplies or favorite toys you wish to donate with the pet

If you need to reschedule, please call 555-SHELTER at least 24 hours in advance.

Is there anything else I can help you with today?"""

        else:
            message = f"""✅ Your case has been submitted successfully!

Case ID: {case_id}

Thank you for contacting animal control. Is there anything else I can help you with today?"""
            
        return message
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Check if user wants another service
        user_input_lower = user_input.lower()
        if any(term in user_input_lower for term in ['yes', 'another', 'something else', 'help']):
            return StateResult.TRANSITION, "DETERMINE_SERVICE", updated_context
        elif any(term in user_input_lower for term in ['no', 'that\'s all', 'nothing else', 'bye', 'goodbye']):
            return StateResult.COMPLETE, None, updated_context
        
        return result, next_state, updated_context

class LLMErrorHandlingState(AnimalControlState):
    """LLM-enhanced state for error handling"""
    
    def __init__(self, database: MockAnimalDatabase):
        system_prompt = """You are AnimalControlBot helping users recover from errors.

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
