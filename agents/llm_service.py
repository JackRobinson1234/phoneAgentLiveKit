import os
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import openai
from dotenv import load_dotenv

from settings import LLM_CONFIG, AVAILABLE_MODELS

# Load environment variables
load_dotenv()

@dataclass
class ToolCall:
    """Represents a tool call from the LLM"""
    name: str
    arguments: Dict[str, Any]
    id: str = None

@dataclass 
class LLMResponse:
    """Represents a response from the LLM"""
    content: str
    tool_calls: List[ToolCall] = None
    usage: Dict[str, int] = None
    model: str = None
    finish_reason: str = None

class OpenRouterService:
    """Service for interacting with OpenRouter API using OpenAI client"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        # Initialize OpenAI client with OpenRouter configuration
        try:
            # Initialize OpenAI client for OpenRouter - minimal config to avoid compatibility issues
            self.client = openai.OpenAI(
                base_url=LLM_CONFIG['api_base_url'],
                api_key=self.api_key
            )
            print("✅ OpenRouter client initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI client: {e}")
            self.client = None
        
        self.default_model = LLM_CONFIG['model']
        self.temperature = LLM_CONFIG['temperature']
        self.max_tokens = LLM_CONFIG['max_tokens']
        self.timeout = LLM_CONFIG['timeout']
        self.retry_attempts = LLM_CONFIG['retry_attempts']
    
    def _test_connection(self):
        """Test the OpenRouter connection with a simple request"""
        if not self.client:
            return False
        
        try:
            # Make a minimal test request
            response = self.client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Make a chat completion request to OpenRouter
        
        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions
            model: Model to use (defaults to configured model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse object
        """
        # Use provided parameters or fall back to defaults
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens or self.max_tokens
        
        # Prepare request parameters
        request_params = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            **kwargs
        }
        
        # Add tools if provided
        if tools and LLM_CONFIG['use_tools']:
            request_params['tools'] = tools
            request_params['tool_choice'] = 'required'  # Force tool usage
        
        # Check if client is available
        if not self.client:
            raise Exception("OpenRouter client not initialized")
        
        try:
            # Add OpenRouter headers to the request
            extra_headers = {
                "HTTP-Referer": "https://github.com/your-repo/HealthAgent",
                "X-Title": "HealthAgent"
            }
            
            # Make the API call with OpenRouter headers
            response = self.client.chat.completions.create(
                extra_headers=extra_headers,
                **request_params
            )
            
            # Extract response data
            message = response.choices[0].message
            content = message.content or ""
            
            # Parse tool calls if present
            tool_calls = []
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_calls.append(ToolCall(
                        name=tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                        id=tool_call.id
                    ))
            
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                usage=response.usage.model_dump() if response.usage else None,
                model=response.model,
                finish_reason=response.choices[0].finish_reason
            )
            
        except Exception as e:
            # Try fallback model if available
            if model != LLM_CONFIG['fallback_model']:
                return self.chat_completion(
                    messages=messages,
                    tools=tools,
                    model=LLM_CONFIG['fallback_model'],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                raise Exception(f"OpenRouter API error: {str(e)}")
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return list(AVAILABLE_MODELS.values())
    
    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        return self.client is not None
    
    def test_connection(self) -> bool:
        """Test the connection to OpenRouter"""
        try:
            response = self.chat_completion([
                {"role": "user", "content": "Hello, please respond with 'OK'"}
            ], model="openai/gpt-3.5-turbo", max_tokens=5)
            return "ok" in response.content.lower()
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

class LLMToolManager:
    """Manages tool definitions for LLM function calling"""
    
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools for animal control"""
        
        # Tool for updating conversation context
        self.register_tool(
            "update_context",
            "Update conversation context with extracted information from user input. ALWAYS update the context with the currently expected field, even for negative, positive (just says yes) or uncertain responses:\n\n1. For negative responses: If user says 'no', 'none', 'doesn't have any', etc., update with appropriate negative values:\n   - For health_issues: 'none reported' or 'no health issues'\n   - For behavioral_issues: 'none reported' or 'no behavioral issues'\n   - For animal_contained: False\n\n2. For uncertain responses: If user says 'not sure', 'I don't know', 'maybe', etc., update with:\n   - 'unknown' or 'not specified' for most fields\n   - For boolean fields like animal_contained, use 'unknown'\n\n3. For ambiguous information: Prioritize updating the field that is currently being collected. For example, if the current missing field is 'surrender_reason' and the user says 'he bites', categorize this as surrender_reason='dog bites' rather than behavioral_issues='biting'. Similarly, if collecting 'animal_condition' and user says 'hit by car', update animal_condition rather than creating a new field.\n\nALWAYS try to match information to the expected field being collected first, before creating new fields. NEVER leave the context unchanged - always update with an appropriate value even for negative or uncertain responses.",
            {
                "type": "object",
                "properties": {
                    "context_updates": {
                        "type": "object",
                        "description": "Key-value pairs to update in the conversation context. ALWAYS update the context with a value for the currently expected field, even for negative or uncertain responses. For negative responses (no, none, doesn't have any), use values like 'none reported', 'no issues', or False for boolean fields. For uncertain responses (not sure, don't know), use 'unknown' or 'not specified'. When possible, categorize information based on the current field being collected.",
                        "additionalProperties": True
                    }
                },
                "required": ["context_updates"]
            }
        )
        
        # Tool for analyzing animal control requests
        self.register_tool(
            "analyze_request",
            "Analyze user input for animal control service needs",
            {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": ["emergency", "found", "lost", "surrender", "info", "other"],
                        "description": "Primary intent of the user"
                    },
                    "animal_type": {
                        "type": "string",
                        "description": "Type of animal mentioned (dog, cat, etc.)"
                    },
                    "service_type": {
                        "type": "string",
                        "enum": ["emergency", "found", "lost", "surrender", "info"],
                        "description": "Type of animal control service needed"
                    },
                    "location": {
                        "type": "string",
                        "description": "Location mentioned in the request"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["emergency", "urgent", "standard", "low"],
                        "description": "Urgency level of the request"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0-1) for the analysis"
                    }
                },
                "required": ["intent", "confidence"]
            }
        )
        
        # Tool for parsing date/time requests
        self.register_tool(
            name="parse_datetime_request",
            description="Parse natural language date and time requests",
            parameters={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Parsed date in YYYY-MM-DD format"
                    },
                    "time": {
                        "type": "string", 
                        "description": "Parsed time in HH:MM format"
                    },
                    "relative_reference": {
                        "type": "string",
                        "description": "Relative time reference like 'tomorrow', 'next week'"
                    },
                    "flexibility": {
                        "type": "string",
                        "enum": ["exact", "morning", "afternoon", "evening", "flexible"],
                        "description": "Time flexibility indicated by user"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score (0-1) for parsed datetime"
                    }
                },
                "required": ["confidence"]
            }
        )
        
        # Tool for generating contextual responses
        self.register_tool(
            name="generate_response",
            description="Generate appropriate response based on conversation state and context",
            parameters={
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "The response message to send to the user. IMPORTANT: For state transitions (when next_action='transition'), this field is optional and will be ignored. The next state's enter method will generate the response instead."
                    },
                    "next_action": {
                        "type": "string",
                        "enum": ["continue", "transition", "error", "complete"],
                        "description": "Recommended next action for the state machine"
                    },
                    "next_state": {
                        "type": "string",
                        "enum": ["GREETING", "EMERGENCY_CASE", "REPORT_FOUND", "REPORT_LOST", "PET_SURRENDER", "SCHEDULE_SURRENDER", "GENERAL_INFO", "CASE_CONFIRMATION", "CASE_COMPLETE", "ERROR_HANDLING", "FINAL_SUMMARY"],
                        "description": "Recommended next state if transitioning. Required when next_action='transition'. Must be one of the valid states in the system."
                    },
                    "context_updates": {
                        "type": "object",
                        "description": "Updates to add to conversation context"
                    }
                },
                "required": ["next_action"]
                # Removed allOf, if/then conditions that aren't supported by OpenRouter
            }
        )
    
    def register_tool(self, name: str, description: str, parameters: Dict[str, Any]):
        """Register a new tool"""
        self.tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
    
    def get_tool(self, name: str) -> Optional[Dict]:
        """Get a specific tool definition"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Dict]:
        """Get all registered tools"""
        return list(self.tools.values())
    
    def get_tools_for_state(self, state_name: str) -> List[Dict]:
        """Get relevant tools for a specific state"""
        state_tool_mapping = {
            # Animal control agent states
            "GREETING": ["analyze_request", "update_context", "generate_response"],
            "EMERGENCY_CASE": ["analyze_request", "update_context", "generate_response"],
            "REPORT_FOUND": ["analyze_request", "update_context", "generate_response"],
            "REPORT_LOST": ["analyze_request", "update_context", "generate_response"],
            "PET_SURRENDER": ["analyze_request", "update_context", "generate_response"],
            "SCHEDULE_SURRENDER": ["parse_datetime_request", "update_context", "generate_response"],
            "GENERAL_INFO": ["analyze_request", "update_context", "generate_response"],
            "CASE_CONFIRMATION": ["update_context", "generate_response"],
            "CASE_COMPLETE": ["update_context", "generate_response"],
            "ERROR_HANDLING": ["update_context", "generate_response"]
        }
        
        # Always include update_context and generate_response as fallbacks
        tool_names = state_tool_mapping.get(state_name, ["update_context", "generate_response"])
        return [self.tools[name] for name in tool_names if name in self.tools]

# Global instances
# Initialize lazily to avoid requiring API key at import time
llm_service = None
tool_manager = None

def get_llm_service():
    """Get or create the global LLM service instance"""
    global llm_service
    if llm_service is None:
        llm_service = OpenRouterService()
    return llm_service

def get_tool_manager():
    """Get or create the global tool manager instance"""
    global tool_manager
    if tool_manager is None:
        tool_manager = LLMToolManager()
    return tool_manager

# Initialize immediately if API key is available (for backward compatibility)
if os.getenv('OPENROUTER_API_KEY'):
    try:
        llm_service = OpenRouterService()
        tool_manager = LLMToolManager()
    except:
        pass  # Will be initialized on first use
