from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import re

from .animal_control_state import AnimalControlState, StateResult
from .context_fields import ContextField

class LLMGreetingAndDetermineServiceState(AnimalControlState):
    """Combined LLM-enhanced greeting and service determination state"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot, an AI assistant for animal control services.

Current State: GREETING - Initial interaction with the user and service determination

Available services:
1. Injured, Abused, or Emergency Cases
2. Report Found Animal
3. Report Lost Animal
4. Schedule Pet Surrender
5. General Information

Your tasks:
1. First, use update_context tool to extract any information provided by the user
2. Then, analyze their input using analyze_request tool
3. Finally, call generate_response tool with appropriate action

Decision logic:
- If user just says "hello" or greets: Respond warmly and present the available services
- If user mentions injured/sick/abused animal or emergency: transition to "EMERGENCY_CASE"
- If user wants to report a found animal: transition to "REPORT_FOUND"
- If user wants to report a lost animal: transition to "REPORT_LOST"
- If user wants to surrender a pet: transition to "PET_SURRENDER"
- If user needs general information: transition to "GENERAL_INFO"
- If unclear: Ask clarifying questions and present the available services

When generating direct responses (not transitions):
- Always acknowledge what the user has said in a natural, conversational way
- If the user's intent is unclear, acknowledge their message and ask clarifying questions
- Be empathetic and professional in your tone
- Tailor your response to the specific context of the conversation

CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response.

CRITICAL: Use update_context tool to extract ANY information the user provides, even if they're just in the greeting state.
For example, if they say "I lost my dog", use update_context to set animal_type="dog" and detected_intent="lost"."""
        
        super().__init__("GREETING", system_prompt)
        
        # Define required fields for different services
        self.service_required_fields = {
            "EMERGENCY_CASE": ['animal_type', 'animal_condition', 'location'],
            "REPORT_FOUND": ['animal_type', 'location_found'],
            "REPORT_LOST": ['animal_type', 'last_seen_location'],
            "PET_SURRENDER": ['animal_type', 'surrender_reason'],
            "GENERAL_INFO": ['info_topic']
        }
    
    # Using the base class implementation for dynamic prompt generation
    
    def generate_contextual_prompt(self, context: Dict[str, Any]) -> str:
        """Generate a contextual prompt for greeting state"""
        # Add available services to context
        context['available_services'] = [
            "Injured, Abused, or Emergency Cases",
            "Report Found Animal",
            "Report Lost Animal",
            "Schedule Pet Surrender",
            "General Information"
        ]
        
        # Let the base class generate the prompt with this context
        return super().generate_contextual_prompt(context)
    
    def get_next_state_name(self, context: Dict[str, Any]) -> Optional[str]:
        """Determine the next state based on context information"""
        # Check if we have a detected intent or service type
        service_type = context.get('service_type')
        detected_intent = context.get('detected_intent')
        
        # Map intents/service types to states
        if service_type == 'emergency' or detected_intent == 'emergency':
            # Check if we have all required fields for emergency case
            if all(field in context for field in self.service_required_fields['EMERGENCY_CASE']):
                return "EMERGENCY_CASE"
        elif service_type == 'found' or detected_intent == 'found':
            # Check if we have all required fields for found animal
            if all(field in context for field in self.service_required_fields['REPORT_FOUND']):
                return "REPORT_FOUND"
        elif service_type == 'lost' or detected_intent == 'lost':
            # Check if we have all required fields for lost animal
            if all(field in context for field in self.service_required_fields['REPORT_LOST']):
                return "REPORT_LOST"
        elif service_type == 'surrender' or detected_intent == 'surrender':
            # Check if we have all required fields for pet surrender
            if all(field in context for field in self.service_required_fields['PET_SURRENDER']):
                return "PET_SURRENDER"
        elif service_type == 'info' or detected_intent == 'info':
            # Check if we have all required fields for general info
            if all(field in context for field in self.service_required_fields['GENERAL_INFO']):
                return "GENERAL_INFO"
        
        # No auto-advance if we don't have enough information
        return None
    
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
        
        # Handle service type transitions based on detected intent or service_type
        service_type = updated_context.get('service_type')
        detected_intent = updated_context.get('detected_intent')
        
        # Only transition for specific service requests, not for greetings or general info
        if detected_intent in ['greeting', 'info', 'other'] or not detected_intent:
            # Stay in the GREETING state for greetings and general messages
            return StateResult.CONTINUE, None, updated_context
            
        # Only transition for specific service types
        if service_type == 'emergency' or detected_intent == 'emergency':
            return StateResult.TRANSITION, "EMERGENCY_CASE", updated_context
        elif service_type == 'found' or detected_intent == 'found':
            return StateResult.TRANSITION, "REPORT_FOUND", updated_context
        elif service_type == 'lost' or detected_intent == 'lost':
            return StateResult.TRANSITION, "REPORT_LOST", updated_context
        elif service_type == 'surrender' or detected_intent == 'surrender':
            return StateResult.TRANSITION, "PET_SURRENDER", updated_context
        
        # Check for keywords in user input as a fallback
        user_input_lower = user_input.lower()
        if any(term in user_input_lower for term in ['emergency', 'injured', 'hurt', 'sick', 'abuse']):
            return StateResult.TRANSITION, "EMERGENCY_CASE", updated_context
        elif any(term in user_input_lower for term in ['found', 'stray']):
            return StateResult.TRANSITION, "REPORT_FOUND", updated_context
        elif any(term in user_input_lower for term in ['lost', 'missing']):
            return StateResult.TRANSITION, "REPORT_LOST", updated_context
        elif any(term in user_input_lower for term in ['surrender', 'give up', 'rehome']):
            return StateResult.TRANSITION, "PET_SURRENDER", updated_context
        elif any(term in user_input_lower for term in ['information', 'services', 'hours', 'locations', 'adoption', 'licensing']):
            # Only transition to GENERAL_INFO for specific information requests
            return StateResult.TRANSITION, "GENERAL_INFO", updated_context
        
        return result, next_state, updated_context

class LLMEmergencyCaseState(AnimalControlState):
    """LLM-enhanced emergency case handling state with step-by-step information collection"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot helping users with emergency animal situations.

Current State: EMERGENCY_CASE - Collecting information about an animal emergency

Your tasks:
1. Use update_context tool to extract ANY information provided by the user
2. Collect information in this order, but ONLY ask for information that hasn't already been provided:
   a. Animal type (dog, cat, bird, etc.)
   b. Animal's condition or injury
   c. Location of the animal
   d. Whether the animal is contained/secured

3. For each interaction:
   - FIRST check what information is already in the context
   - Ask ONLY for the NEXT SINGLE missing piece of information
   - NEVER ask for information that's already in the context
   - If user provides multiple pieces of information at once, acknowledge and extract all provided info
   - Move to the next missing information

4. When generating responses:
   - ALWAYS acknowledge the MOST RECENTLY provided information first
   - For example, if user just told you the location, start with "Thank you for letting me know the animal is at [location]."
   - If they just provided condition information, acknowledge that: "I understand the [animal_type] is [condition]."
   - Only after acknowledging recent information, ask for the next piece of information

5. Provide immediate guidance based on the situation
6. Use generate_response with appropriate next_action

CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response.

CRITICAL: For true emergencies, emphasize the importance of calling the emergency hotline immediately.
CRITICAL: Be conversational and natural. Don't use rigid templates. Adapt your responses based on the context.
CRITICAL: NEVER ask for information that's already been provided. For example, if the context already contains animal_condition='coughing up blood', NEVER ask about the condition again.
CRITICAL: NEVER start your response with generic phrases like "I understand there's an emergency" when you have more specific information. Always acknowledge the most recent information first."""
        
        # Add specialized transition prompts for when transitioning from different states
        self.transition_prompts = {
            "GREETING": """You are now helping a user with an animal emergency situation.
            
When responding to the user:
1. Acknowledge the emergency nature of their situation
2. Express urgency while remaining calm and professional
3. Acknowledge any information they've already shared (animal type, condition, etc.)
4. For critical emergencies (severe injuries, life-threatening situations), immediately provide the emergency hotline number
5. Begin gathering missing information in a focused, efficient manner
6. Don't ask for information they've already provided

Your tone should be urgent but reassuring, focusing on getting the critical information as quickly as possible."""
        }
        
        super().__init__("EMERGENCY_CASE", system_prompt)
        self.required_fields = [
            ContextField.ANIMAL_TYPE.value,        # Step 1a
            ContextField.ANIMAL_CONDITION.value,   # Step 1b
            ContextField.LOCATION.value,           # Step 1c
            ContextField.ANIMAL_CONTAINED.value    # Step 1d
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'GREETING'))
    
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
        
        # Otherwise, use the LLM-generated response
        # Do not override with hardcoded prompts - let the LLM handle the conversation flow
        # The message should already be set by process_input_with_llm
        
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
            
    def get_next_state_name(self, context: Dict[str, Any]) -> Optional[str]:
        """Determine the next state based on context information"""
        # If all required fields are present, move to case confirmation
        if all(field in context for field in self.required_fields):
            return "CASE_CONFIRMATION"
        return None

class LLMReportFoundState(AnimalControlState):
    """LLM-enhanced state for reporting found animals with step-by-step information collection"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot helping users report found animals.

Current State: REPORT_FOUND - Collecting information about a found animal

Your tasks:
1. Use update_context tool to extract ANY information provided by the user
2. Collect information in this order, but ONLY ask for information that hasn't already been provided:
   a. Animal type (dog, cat, bird, etc.) and breed if known
   b. Color, size, and distinctive markings
   c. Where and when the animal was found
   d. Identifying features (collar, tags, microchip)
   e. Whether the finder can temporarily keep the animal

3. For each interaction:
   - FIRST check what information is already in the context
   - Ask ONLY for the NEXT SINGLE missing piece of information
   - NEVER ask for information that's already in the context
   - If user provides multiple pieces of information at once, acknowledge and extract all provided info
   - Move to the next missing information

4. When generating responses:
   - ALWAYS acknowledge the MOST RECENTLY provided information first
   - For example, if user just told you the location, start with "Thank you for letting me know the animal was found at [location]."
   - If they just provided breed and color information, acknowledge that: "I've noted that you found a [color] [breed]."
   - Only after acknowledging recent information, ask for the next piece of information

5. Use generate_response with appropriate next_action

CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response.

CRITICAL: Be conversational and natural. Don't use rigid templates. Adapt your responses based on the context and what information is already available.

CRITICAL: NEVER ask for information that's already been provided. For example, if the context already contains animal_color='brown', NEVER ask about the color again.

CRITICAL: NEVER start your response with generic phrases like "I understand you found a dog" when you have more specific information. Always acknowledge the most recent information first."""
        
        # Add specialized transition prompts for when transitioning from different states
        self.transition_prompts = {
            "GREETING": """You are now helping a user who has just indicated they've found an animal.
            
When responding to the user:
1. Thank them for reporting the found animal
2. Acknowledge any information they've already shared (animal type, location, etc.)
3. Explain briefly that you'll help them create a found animal report
4. Begin gathering missing information in a conversational way
5. Don't ask for information they've already provided

Your tone should be appreciative and helpful while efficiently collecting the needed information."""
        }
        
        super().__init__("REPORT_FOUND", system_prompt)
        self.required_fields = [
            ContextField.ANIMAL_TYPE.value,          # Step 1a
            ContextField.ANIMAL_DESCRIPTION.value,   # Step 1b
            ContextField.LOCATION_FOUND.value,       # Step 1c
            ContextField.IDENTIFYING_FEATURES.value, # Step 1d
            ContextField.FINDER_CAN_KEEP.value       # Step 1e
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'GREETING'))
    
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
                'description': updated_context.get('animal_description', 'Unknown'),
                'location_found': updated_context.get('location_found'),
                'identifying_features': updated_context.get('identifying_features', 'None'),
                'finder_can_keep': updated_context.get('finder_can_keep', 'Unknown'),
                'timestamp': datetime.now().isoformat()
            }
            
            # Add a message to the context indicating all information has been collected
            updated_context['message'] = "Thank you for providing all the necessary information about this found animal. Let me summarize what we have so far."
            
            return StateResult.TRANSITION, "CASE_CONFIRMATION", updated_context
        
        # Otherwise, use the LLM-generated response
        # Do not override with hardcoded prompts - let the LLM handle the conversation flow
        # The message should already be set by process_input_with_llm
        
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
            
    def get_next_state_name(self, context: Dict[str, Any]) -> Optional[str]:
        """Determine the next state based on context information"""
        # If all required fields are present, move to case confirmation
        if all(field in context for field in self.required_fields):
            return "CASE_CONFIRMATION"
        return None

class LLMReportLostState(AnimalControlState):
    """LLM-enhanced state for reporting lost animals with step-by-step information collection"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot helping users report lost animals.

Current State: REPORT_LOST - Collecting information about a lost animal

Your tasks:
1. Use update_context tool to extract ANY information provided by the user
2. Collect information in this order, but ONLY ask for information that hasn't already been provided:
   a. Animal type (dog, cat, bird, etc.), breed, and name
   b. Color, size, and any distinctive markings
   c. Where and when the animal was last seen
   d. Identifying features (collar, tags, microchip)
   e. Owner contact information (name and phone number)

3. For each interaction:
   - FIRST check what information is already in the context
   - Ask ONLY for the NEXT SINGLE missing piece of information
   - NEVER ask for information that's already in the context
   - If user provides multiple pieces of information at once, acknowledge and extract all provided info
   - Move to the next missing information

4. When generating responses:
   - ALWAYS acknowledge the MOST RECENTLY provided information first
   - For example, if user just told you the location, start with "Thank you for letting me know your pet was last seen at [location]."
   - If they just provided breed and color information, acknowledge that: "I've noted that your [animal_type] is a [color] [breed]."
   - Only after acknowledging recent information, ask for the next piece of information

5. Use generate_response with appropriate next_action

CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response.

CRITICAL: Be conversational and natural. Don't use rigid templates. Adapt your responses based on the context and what information is already available.

CRITICAL: NEVER ask for information that's already been provided. For example, if the context already contains animal_color='green', NEVER ask about the color again.

CRITICAL: NEVER start your response with generic phrases like "I understand you're looking for your dog" when you have more specific information. Always acknowledge the most recent information first."""
        
        # Add specialized transition prompt for when transitioning from GREETING to REPORT_LOST
        self.transition_prompts = {
            "GREETING": """You are now helping a user who has just indicated they've lost a pet.
            
When responding to the user:
1. Express empathy about their lost pet
2. Acknowledge any information they've already shared (pet name, type, etc.)
3. Explain briefly that you'll help them create a lost pet report
4. Begin gathering missing information in a conversational way
5. Don't ask for information they've already provided

Your tone should be supportive and reassuring while efficiently collecting the needed information."""
        }
        
        super().__init__("REPORT_LOST", system_prompt)
        self.required_fields = [
            ContextField.ANIMAL_TYPE.value,          # Step 1a
            ContextField.ANIMAL_DESCRIPTION.value,   # Step 1b
            ContextField.LAST_SEEN_LOCATION.value,   # Step 1c
            ContextField.IDENTIFYING_FEATURES.value, # Step 1d
            ContextField.OWNER_CONTACT.value         # Step 1e
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'GREETING'))
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Validate contact information if provided
        if updated_context.get('owner_contact') and not self._validate_contact(updated_context['owner_contact']):
            updated_context['contact_validation_error'] = True
            # Remove invalid contact so we'll ask for it again
            del updated_context['owner_contact']
        
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
            
            # Auto-transition to confirmation state when all fields are complete
            return StateResult.TRANSITION, "CASE_CONFIRMATION", updated_context
        
        # Auto-transition if the LLM requested a transition and we have enough information
        if result == StateResult.TRANSITION and next_state and len(missing_fields) <= 1:
            # We're only missing one field, but the LLM wants to transition
            # This allows for more natural conversation flow
            return result, next_state, updated_context
        
        # Otherwise, ask for the next piece of information
        next_field = missing_fields[0]
        prompt_message = self._get_prompt_for_field(next_field, updated_context)
        
        # Only override the message if the LLM didn't provide a good follow-up question
        if not updated_context.get('message') or 'thank you' in updated_context.get('message', '').lower():
            updated_context['message'] = prompt_message
        
        return StateResult.CONTINUE, None, updated_context
    
    def get_next_state_name(self, context: Dict[str, Any]) -> Optional[str]:
        """Determine the next state based on context information"""
        # If all required fields are present, move to case confirmation
        if all(field in context for field in self.required_fields):
            return "CASE_CONFIRMATION"
        return None
        
    def _validate_contact(self, contact: str) -> bool:
        """Validate contact information format"""
        # If we get here, the error handling failed
        return "I'm sorry, but I encountered an error. Please try again or contact support."
        if re.match(r'^\d{10}$', cleaned):
            return True
            
        return False
    
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
        
        # Add validation error message if needed
        if field == 'owner_contact' and context.get('contact_validation_error'):
            prompts['owner_contact'] = "I couldn't validate the contact information you provided. Please provide a valid phone number (10 digits) or email address."
        
        # Calculate progress
        total_fields = len(self.required_fields)
        completed_fields = total_fields - len(self._get_missing_fields(context))
        progress_percent = int((completed_fields / total_fields) * 100)
        progress_bar = f"[Progress: {progress_percent}% - Step {completed_fields + 1} of {total_fields}]"
        
        # Acknowledge information already provided
        acknowledgment = ""
        if context.get('animal_type'):
            acknowledgment += f"I have that your lost pet is a {context.get('animal_type')}. "
        if context.get('animal_name'):
            acknowledgment += f"Their name is {context.get('animal_name')}. "
        
        # Combine progress bar with prompt
        if acknowledgment:
            return f"{progress_bar}\n\n{acknowledgment}\n\n{prompts[field]}"
        else:
            return f"{progress_bar}\n\n{prompts[field]}"

class LLMPetSurrenderState(AnimalControlState):
    """LLM-enhanced state for pet surrender scheduling with step-by-step information collection"""
    
    def __init__(self):
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
        self.required_fields = [
            ContextField.ANIMAL_TYPE.value,       # Step 1a
            ContextField.SURRENDER_REASON.value,  # Step 1b
            ContextField.HEALTH_ISSUES.value,     # Step 1c (combines medical and behavioral)
            ContextField.OWNER_CONTACT.value      # Step 1d
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'GREETING'))
    
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
            'owner_contact': "Please provide your contact information (name and phone number) so we can reach you if needed."
        }
        
        # Acknowledge information already provided
        acknowledgment = ""
        pet_type = context.get('animal_type', '')
        if pet_type:
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
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot scheduling pet surrender appointments.

Current State: SCHEDULE_SURRENDER - Scheduling a surrender appointment

Your tasks:
1. Present available dates and times for surrender appointments
2. Help user select a convenient time
3. Confirm the appointment details
4. Use generate_response with appropriate next_action

CRITICAL: Ensure the user understands the surrender process and what to bring."""
        
        super().__init__("SCHEDULE_SURRENDER", system_prompt)
    
    def generate_contextual_prompt(self, context: Dict[str, Any]) -> str:
        """Generate a contextual prompt with available dates"""
        # In a real system, these would come from a database
        available_dates = [
            "Monday, October 5 (10:00 AM - 2:00 PM)",
            "Wednesday, October 7 (1:00 PM - 4:00 PM)",
            "Friday, October 9 (9:00 AM - 12:00 PM)"
        ]
        
        # Add dates to context for later reference
        context['available_dates'] = available_dates
        
        # Let the base class generate the prompt with this context
        return super().generate_contextual_prompt(context)
    
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
        
    def get_next_state_name(self, context: Dict[str, Any]) -> Optional[str]:
        """Determine the next state based on context information"""
        # If we have a selected date, move to case confirmation
        if context.get('selected_date'):
            return "CASE_CONFIRMATION"
        return None

class LLMGeneralInfoState(AnimalControlState):
    """LLM-enhanced state for providing general information"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot providing general information about animal control services.

Current State: GENERAL_INFO - Providing general information about services

Your tasks:
1. Answer general questions about animal control services
2. Provide information about adoption, licensing, wildlife, etc.
3. Direct users to specific services if needed
4. Use generate_response with appropriate next_action

CRITICAL: Be informative and helpful, directing users to specific services when appropriate."""
        
        super().__init__("GENERAL_INFO", system_prompt)
    
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
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot confirming case details with the user.

Current State: CASE_CONFIRMATION - Confirming case details and providing next steps

Your tasks:
1. Summarize the collected information
2. Confirm details with the user
3. Provide appropriate next steps based on the case type
4. Use generate_response with appropriate next_action

CRITICAL: Ensure all necessary information has been collected and provide clear next steps."""
        
        super().__init__("CASE_CONFIRMATION", system_prompt)
    
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
    
    def __init__(self):
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
    
    def enter(self, context: Dict[str, Any]) -> str:
        return """Hello! Welcome to Animal Control Services. How can I assist you today?"""
        return (f"{error_message}\n\n"
                f"Would you like to:\n"
                f"1. Start over\n"
                f"2. Try again\n"
                f"3. End conversation\n\n"
                f"Please select an option.")
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        return self.process_input_with_llm(user_input, context)


class LLMFinalSummaryState(AnimalControlState):
    """LLM-enhanced state for final summary and call completion"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot providing a final summary of the conversation.

Current State: FINAL_SUMMARY - Summarizing all collected information and ending the call

Your tasks:
1. Thank the user for contacting Animal Control Services
2. Summarize ALL the information collected during the conversation
3. Provide a clear case ID or reference number if applicable
4. Explain what will happen next (e.g., dispatch of animal control officer, follow-up call, etc.)
5. Ask if there's anything else the user needs before ending the call

When generating your response:
- Be thorough in your summary - include ALL details the user has provided
- Organize the information in a clear, structured format
- Be warm and professional in your tone
- Assure the user that their case will be handled appropriately

Use generate_response with appropriate next_action (usually 'complete' to end the conversation)

CRITICAL: This is the final state, so make sure your summary is comprehensive and leaves the user with a clear understanding of what will happen next."""
        
        super().__init__("FINAL_SUMMARY", system_prompt)
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a comprehensive summary based on the context"""
        # Determine the case type
        case_type = context.get('service_type', 'general')
        
        # Generate a case ID if not already present
        if not context.get('case_id'):
            import random
            case_id = f"AC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            context['case_id'] = case_id
        
        # Let the LLM generate the actual summary content using the enhanced prompt
        return self.process_state_entry(context, context.get('previous_state', 'UNKNOWN'))
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        """Process user input in the final summary state"""
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Check for conversation ending keywords
        user_input_lower = user_input.lower().strip()
        if any(term in user_input_lower for term in ['bye', 'goodbye', 'thanks', 'thank you', 'that\'s all', 'done']):
            return StateResult.COMPLETE, None, updated_context
        
        # Check for new service request
        if any(term in user_input_lower for term in ['new', 'another', 'different', 'start over']):
            return StateResult.TRANSITION, "GREETING", updated_context
        
        return result, next_state, updated_context


class LLMErrorHandlingState(AnimalControlState):
    """LLM-enhanced error handling state"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot handling an error situation.

Current State: ERROR_HANDLING - Helping the user recover from an error

Your tasks:
1. Acknowledge the error that occurred
2. Offer recovery options (start over, try again, or end conversation)
3. Use the generate_response tool to provide your response

When the user wants to start over, set next_action="transition" and next_state="GREETING".
When the user wants to try again, set next_action="transition" and next_state equal to the previous_state in context.
When the user wants to end the conversation, set next_action="complete".

CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response."""
        
        super().__init__("ERROR_HANDLING", system_prompt)
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'UNKNOWN'))
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        """Process user input in the error handling state"""
        return self.process_input_with_llm(user_input, context)
