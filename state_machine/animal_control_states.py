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

Your tasks:
1. First, use update_context tool to extract any information provided by the user
2. Then, analyze their input using analyze_request tool
3. Finally, call generate_response tool with appropriate action

Decision logic:
- If user just says "hello" or greets: Respond warmly with a simple greeting
- If user asks about available services or options: List all available services
- If user mentions injured/sick/abused animal or emergency: transition to "EMERGENCY_CASE"
- If user wants to report a found animal: transition to "REPORT_FOUND"
- If user wants to report a lost animal: transition to "REPORT_LOST"
- If user wants to surrender a pet: transition to "PET_SURRENDER"
- If unclear: Ask clarifying questions without listing all services

When generating direct responses (not transitions):
- Always acknowledge what the user has said in a natural, conversational way
- If the user's intent is unclear, acknowledge their message and ask clarifying questions
- Be empathetic and professional in your tone
- Tailor your response to the specific context of the conversation
- When user asks about available services or what you can help with, respond with a complete list of services:
  ```
  I can help you with the following animal control services:
  
  1. Emergency assistance for injured or abused animals
  2. Help with found animals
  3. Lost pet reporting
  4. Pet surrender scheduling
  
  What would you like assistance with today?
  ```
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response.

CRITICAL: Use update_context tool to extract ANY information the user provides, even if they're just in the greeting state.
For example, if they say "I lost my dog", use update_context to set animal_type="dog" and detected_intent="lost"."""
        
        super().__init__("GREETING", system_prompt)
        
        # Define required fields for different services
        self.service_required_fields = {
            "EMERGENCY_CASE": ['animal_type', 'animal_condition', 'location'],
            "REPORT_FOUND": ['animal_type', 'location_found'],
            "REPORT_LOST": ['animal_type', 'last_seen_location'],
            "PET_SURRENDER": ['animal_type', 'surrender_reason']        }
    
    # Using the base class implementation for dynamic prompt generation
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Return a default short greeting instead of making an LLM call"""
        return "Hello! I'm the Animal Control Services assistant. How can I help you today?"
    
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
        # Temporarily disabled GENERAL_INFO transitions
        # elif service_type == 'info' or detected_intent == 'info':
        #     # Check if we have all required fields for general info
        #     if all(field in context for field in self.service_required_fields['GENERAL_INFO']):
        #         return "GENERAL_INFO"
        
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
                    # 5: "GENERAL_INFO"  # Temporarily disabled
                }
                return StateResult.TRANSITION, service_map[selection], updated_context
        except ValueError:
            pass
        
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
   - DO NOT include any step indicators or progress information in your responses

5. Provide immediate guidance based on the situation
6. Use generate_response with appropriate next_action

FIELD CATEGORIZATION GUIDELINES:
When users provide ambiguous information, categorize it according to these rules:

- ANIMAL_TYPE: The species or category of animal (dog, cat, bird, etc.)
  Example: "It's a German Shepherd" → animal_type="dog", animal_breed="German Shepherd"
  Example: "There's a hawk with a broken wing" → animal_type="bird", animal_condition="broken wing"

- ANIMAL_CONDITION: Physical state, injuries, or health concerns
  Example: "It's bleeding from its leg" → animal_condition="bleeding leg"
  Example: "The dog seems to be choking" → animal_condition="choking"
  Example: "It looks like it was hit by a car" → animal_condition="possible vehicle injury"

- LOCATION: Where the animal is currently located
  Example: "It's in my backyard" → location="caller's backyard"
  Example: "Corner of Main St and Oak Ave" → location="Main St and Oak Ave"

- ANIMAL_CONTAINED: Whether the animal is secured, contained, or free to move
  Example: "I've got it in my garage" → animal_contained=True
  Example: "It's running loose in the park" → animal_contained=False
  Example: "We put it in a box" → animal_contained=True

- OWNER_CONTACT: Contact information for the owner of the animal
  Example: "My phone number is 555-1234" → owner_contact="555-1234"
  Example: "My email is johndoe@example.com" → owner_contact="johndoe@example.com"
  Example: "My name is John Doe" → owner_contact="John Doe"

When a response could fit multiple categories, prioritize as follows:
1. If it describes the species, update animal_type
2. If it describes injuries or condition, update animal_condition
3. If it describes where the animal is, update location
4. If it describes containment status, update animal_contained

Example of ambiguous response: "There's an injured cat in my yard but it keeps running away"
- Primary categorization: animal_type="cat"
- Secondary categorization: animal_condition="injured"
- Additional categorization: location="caller's yard", animal_contained=False

VALID STATE TRANSITIONS:
When all required information is collected, transition to CASE_CONFIRMATION state using:
next_action='transition', next_state='CASE_CONFIRMATION'

VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
DO NOT use any state names that aren't in this list:
- GREETING
- EMERGENCY_CASE
- REPORT_FOUND
- REPORT_LOST
- PET_SURRENDER
- SCHEDULE_SURRENDER
- CASE_CONFIRMATION
- CASE_COMPLETE
- ERROR_HANDLING
- FINAL_SUMMARY

CRITICAL: For true emergencies, emphasize the importance of calling the emergency hotline immediately.
CRITICAL: Be conversational and natural. Don't use rigid templates. Adapt your responses based on the context.
CRITICAL: NEVER ask for information that's already been provided. For example, if the context already contains animal_condition='coughing up blood', NEVER ask about the condition again.
CRITICAL: NEVER start your response with generic phrases like "I understand there's an emergency" when you have more specific information. Always acknowledge the most recent information first.

CRITICAL HANDLING OF UNCLEAR INPUTS:
- When user input is unclear, vague, or you're not sure how to interpret it, ALWAYS use generate_response
- NEVER fall back to generic responses like "I'm not sure how to respond"
- Instead, ask specific clarifying questions through generate_response
- For example: If user says "not sure" about location, use generate_response to ask "Could you tell me approximately where you last saw the animal? Even a general area or neighborhood would help."
- Always maintain the conversation flow by using generate_response to ask for clarification"""
        
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

VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
Your tone should be urgent but reassuring, focusing on getting the critical information as quickly as possible."""
        }
        
        super().__init__("EMERGENCY_CASE", system_prompt)
        self.required_fields = [
            ContextField.ANIMAL_TYPE.value,        # Step 1a
            ContextField.ANIMAL_CONDITION.value,   # Step 1b
            ContextField.LOCATION.value,           # Step 1c
            ContextField.ANIMAL_CONTAINED.value, # Step 1d
            ContextField.OWNER_CONTACT.value    # Step 1d
        ]
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'GREETING'))
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        
        # Special handling for animal_contained boolean field
        # If animal_contained is False, it should be considered as present, not missing
        if 'animal_contained' in updated_context:
            print(f"ANIMAL CONTAINED VALUE: {updated_context['animal_contained']}")
        
        # Custom check for missing fields that handles boolean values properly
        missing_fields = []
        for field in self.required_fields:
            if field == 'animal_contained':
                # Only consider animal_contained missing if it's not in the context at all
                if field not in updated_context:
                    missing_fields.append(field)
            else:
                # For other fields, use the standard check
                if not updated_context.get(field):
                    missing_fields.append(field)
        
        print("MISSING FIELDS: ", missing_fields)
        
        # If we have all required information, prepare to transition
        if not missing_fields:
            print("SHOULD TRANSITION!!!!")
            # Create case details from collected information
            updated_context['case_details'] = {
                'type': 'emergency',
                'animal_type': updated_context.get('animal_type'),
                'condition': updated_context.get('animal_condition', 'Unknown'),
                'location': updated_context.get('location'),
                'contained': updated_context.get('animal_contained', 'Unknown'),
                'timestamp': datetime.now().isoformat()
            }
                        
            return StateResult.TRANSITION, "CASE_CONFIRMATION", updated_context
        print("NOT BEING TRANSITIONED, MISSING FIELDS!!!!")
        return StateResult.CONTINUE, None, updated_context
    
    def _get_missing_fields(self, context: Dict[str, Any]) -> list:
        """Determine which required fields are still missing"""
        return [field for field in self.required_fields if field not in context]
            
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
   - DO NOT include any step indicators or progress information in your responses

5. Use generate_response with appropriate next_action

CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response.

CRITICAL: Be conversational and natural. Don't use rigid templates. Adapt your responses based on the context and what information is already available.

CRITICAL: NEVER ask for information that's already been provided. For example, if the context already contains animal_color='brown', NEVER ask about the color again.

CRITICAL: NEVER start your response with generic phrases like "I understand you found a dog" when you have more specific information. Always acknowledge the most recent information first."""
        
        # Add specialized transition prompt for when transitioning from GREETING to REPORT_FOUND
        self.transition_prompts = {
            "GREETING": """You are now helping a user who has just indicated they've found an animal.
            
When responding to the user:
1. Thank them for reporting the found animal
2. Acknowledge any information they've already shared (animal type, location, etc.)
3. Explain briefly that you'll help them create a found animal report
4. Begin gathering missing information in a conversational way
5. Don't ask for information they've already provided
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points
VALID STATE TRANSITIONS:
When all required information is collected, transition to CASE_CONFIRMATION state using:
next_action='transition', next_state='CASE_CONFIRMATION'
CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
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
        return result, next_state, updated_context
    
    def _get_missing_fields(self, context: Dict[str, Any]) -> list:
        """Determine which required fields are still missing"""
        return [field for field in self.required_fields if field not in context]
    
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
   - DO NOT include any step indicators or progress information in your responses
   - Be empathetic since this is about a lost pet
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
5. Use generate_response with appropriate next_action

CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response.

CRITICAL: Be conversational and natural. Don't use rigid templates. Adapt your responses based on the context and what information is already available.

CRITICAL: NEVER ask for information that's already been provided. For example, if the context already contains animal_color='green', NEVER ask about the color again.

CRITICAL: NEVER start your response with generic phrases like "I understand you're looking for your dog" when you have more specific information. Always acknowledge the most recent information first."""
        
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
        return result, next_state, updated_context
    
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
        return [field for field in self.required_fields if field not in context]    
    # Removed hardcoded _get_prompt_for_field method - now handled by LLM

class LLMPetSurrenderState(AnimalControlState):
    """LLM-enhanced state for pet surrender scheduling with step-by-step information collection"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot helping users schedule pet surrenders.

Current State: PET_SURRENDER - Collecting information for pet surrender

Your tasks:
1. Use update_context tool to extract ANY information provided by the user
2. Collect information in this order, but ONLY ask for information that hasn't already been provided:
   a. Animal type (dog, cat, etc.), breed, age, and name
   b. Reason for surrender
   c. Medical or behavioral issues
   d. Owner contact information (name and phone number)

3. For each interaction:
   - FIRST check what information is already in the context
   - Ask ONLY for the NEXT SINGLE missing piece of information
   - NEVER ask for information that's already in the context
   - If user provides multiple pieces of information at once, acknowledge and extract all provided info
   - Move to the next missing information

4. When generating responses:
   - ALWAYS acknowledge the MOST RECENTLY provided information first
   - For example, if user just told you the reason, start with "Thank you for explaining why you need to surrender your pet."
   - If they just provided health information, acknowledge that: "I understand your [animal_type] has [health_issue]."
   - Only after acknowledging recent information, ask for the next piece of information
   - DO NOT include any step indicators or progress information in your responses
   - Be empathetic but professional about the pet surrender process

5. Use generate_response with appropriate next_action

FIELD CATEGORIZATION GUIDELINES:
When users provide ambiguous information, categorize it according to these rules:

- SURRENDER_REASON: Information about WHY they're giving up the pet (moving, allergies, can't afford, landlord issues, no time)
  Example: "I'm moving to an apartment that doesn't allow pets" → surrender_reason
  Example: "My landlord doesn't allow dogs" → surrender_reason

- HEALTH_ISSUES: Physical health problems or medical conditions
  Example: "The dog has arthritis" → health_issues
  Example: "She needs special food for her kidney disease" → health_issues

- BEHAVIORAL_ISSUES: Behavior problems, temperament issues, or training concerns
  Example: "The dog bites people" → behavioral_issues
  Example: "She's not good with children" → behavioral_issues
  Example: "He's aggressive toward other dogs" → behavioral_issues

When a response could fit multiple categories, prioritize as follows:
1. If it describes WHY they're surrendering, use surrender_reason
2. If it describes behavior problems, use behavioral_issues
3. If it describes medical conditions, use health_issues

Example of ambiguous response: "I can't keep him because he bites"
- Primary categorization: surrender_reason="dog bites"
- Secondary categorization: behavioral_issues="biting behavior"
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response.

CRITICAL: Be conversational and natural. Don't use rigid templates. Adapt your responses based on the context and what information is already available.

CRITICAL: NEVER ask for information that's already been provided. For example, if the context already contains surrender_reason='moving', NEVER ask about the reason again.

CRITICAL: NEVER start your response with generic phrases like "I understand you want to surrender your pet" when you have more specific information. Always acknowledge the most recent information first.

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
        return result, next_state, updated_context
        
    def _get_missing_fields(self, context: Dict[str, Any]) -> list:
        """Determine which required fields are still missing"""
        return [field for field in self.required_fields if field not in context]
    
    # Removed hardcoded _get_prompt_for_field method - now handled by LLM

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
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
CRITICAL: Ensure the user understands the surrender process and what to bring."""
        
        super().__init__("SCHEDULE_SURRENDER", system_prompt)
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'PET_SURRENDER'))
    
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
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
CRITICAL: Be informative and helpful, directing users to specific services when appropriate.
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
CRITICAL: Clearly state this is the end of the call. Tell the user their case has been submitted and what will happen next.
CRITICAL: End with "Thank you for calling Animal Control Services. Goodbye." to signal the end of the conversation.
"""
        
        super().__init__("FO", system_prompt)
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'GREETING'))
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        return result, next_state, updated_context

class LLMCaseConfirmationState(AnimalControlState):
    """LLM-enhanced state for case confirmation"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot confirming case details with the user.

Current State: CASE_CONFIRMATION - Confirming case details and providing next steps
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
Your tasks:
1. Summarize the collected information
2. Confirm details with the user
3. Provide appropriate next steps based on the case type
4. Use generate_response with appropriate next_action

CRITICAL: Clearly state this is the end of the call. Tell the user their case has been submitted and what will happen next.
CRITICAL: End with "Thank you for calling Animal Control Services. Goodbye." to signal the end of the conversation.
"""
        
        super().__init__("CASE_CONFIRMATION", system_prompt)
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'GREETING'))
 
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        result, next_state, updated_context = self.process_input_with_llm(user_input, context)
        return result, next_state, updated_context
class LLMCaseCompleteState(AnimalControlState):
    """LLM-enhanced state for case completion"""
    
    def __init__(self):
        system_prompt = """You are AnimalControlBot confirming case submission and providing final information.

Current State: CASE_COMPLETE - Confirming case submission and providing next steps

VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

Your tasks:
1. Confirm the case has been submitted
2. Provide the case ID for reference
3. Explain what happens next briefly
4. End the call with a clear goodbye message

CRITICAL: Clearly state this is the end of the call. Tell the user their case has been submitted and what will happen next.
CRITICAL: End with "Thank you for calling Animal Control Services. Goodbye." to signal the end of the conversation.
CRITICAL: Do not ask if there's anything else the user needs - this is the end of the call."""
        
        super().__init__("CASE_COMPLETE", system_prompt)
    
    def enter(self, context: Dict[str, Any]) -> str:
        case_details = context.get('case_details', {})
        case_type = case_details.get('type', 'unknown')
        case_id = context.get('case_id', 'UNKNOWN-ID')
        
        if case_type == 'emergency':
            message = f"""✅ Your emergency animal case has been submitted successfully! Case ID: {case_id}.

An animal control officer will be dispatched to the location immediately. For urgent assistance, call our emergency hotline at 555-ANIMAL.

This concludes our call. Thank you for calling Animal Control Services. Goodbye."""

        elif case_type == 'found':
            message = f"""✅ Your found animal report has been submitted successfully! Case ID: {case_id}.

An officer will contact you within 24 hours. We'll check for matching lost pet reports and provide guidance if you're keeping the animal temporarily.

This concludes our call. Thank you for calling Animal Control Services. Goodbye."""

        elif case_type == 'lost':
            message = f"""✅ Your lost pet report has been submitted successfully! Case ID: {case_id}.

We'll check our found animal reports and alert our field officers to look for your pet. We recommend also posting on local lost pet websites and social media.

This concludes our call. Thank you for calling Animal Control Services. Goodbye."""

        elif case_type == 'surrender':
            appointment_date = case_details.get('appointment_date', 'Not scheduled')
            message = f"""✅ Your pet surrender appointment has been confirmed! Case ID: {case_id}, Appointment: {appointment_date}.

Please bring your photo ID and any pet medical records or supplies you wish to donate. If you need to reschedule, call 555-SHELTER at least 24 hours in advance.

This concludes our call. Thank you for calling Animal Control Services. Goodbye."""

        else:
            message = f"""✅ Your case has been submitted successfully! Case ID: {case_id}.

We'll process your request and contact you if we need additional information.

This concludes our call. Thank you for calling Animal Control Services. Goodbye."""
            
        return message
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        # Since this is the end of the call, we don't need to process further input
        # Just return the same state and context
        return StateResult.CONTINUE, None, context

    
    def enter(self, context: Dict[str, Any]) -> str:
        return "Hello! Welcome to Animal Control Services. How can I assist you today?"


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
VOICE OPTIMIZATION REQUIREMENTS:
1. Keep all responses under 3 sentences when possible
2. Use simple, direct language suitable for voice
3. Avoid long lists or complex explanations
4. Focus on the most important information only
5. Break complex topics into simple, digestible points

CRITICAL: Be concise and direct. Voice users need short, clear responses they can easily understand and remember.
CRITICAL: When transitioning to a new state, ONLY use the generate_response tool with next_action='transition' and next_state='STATE_NAME'. DO NOT include a response message - the next state will generate the appropriate response."""
        
        super().__init__("ERROR_HANDLING", system_prompt)
    
    def enter(self, context: Dict[str, Any]) -> str:
        """Generate a response using the LLM when entering the state"""
        # Use the process_state_entry method to generate a response with the LLM
        return self.process_state_entry(context, context.get('previous_state', 'UNKNOWN'))
    
    def process_input(self, user_input: str, context: Dict[str, Any]) -> Tuple[StateResult, Optional[str], Dict[str, Any]]:
        """Process user input in the error handling state"""
        return self.process_input_with_llm(user_input, context)
