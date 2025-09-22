"""
Integration of llm_eval with healthAgent

This example demonstrates how to use the llm_eval decorator to evaluate
the behavior of the healthAgent's LLM service.
"""

import sys
import os
from typing import Dict, List, Any
from datetime import datetime

# Add parent directory to path to import healthAgent modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add llm-eval-mvp to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "llm-eval-mvp"))

# Import llm_eval functionality
from llm_eval import llm_eval, get_traces, clear_traces

# Import healthAgent functionality
from agents.llm_service import llm_service, tool_manager
from state_machine.llm_states import LLMGreetingState
from models.database import MockDatabase

# Define rules for healthAgent evaluation
HEALTH_AGENT_RULES = [
    "always extract patient information when provided",
    "never provide medical diagnoses",
    "always maintain patient confidentiality",
    "use appropriate tools for each state"
]

# Define a custom validator function
def validate_appointment_scheduling(trace):
    """Ensure appointment scheduling follows business rules."""
    # Check if this is an appointment scheduling interaction
    is_appointment = False
    for message in trace.messages:
        if "appointment" in message.get("content", "").lower():
            is_appointment = True
            break
    
    if not is_appointment:
        return True, "Not an appointment scheduling interaction"
    
    # Check if appropriate tools were used
    appointment_tools = ["analyze_appointment_request", "parse_datetime_request"]
    tool_used = False
    
    for tool_call in trace.tool_calls:
        if tool_call.get("name") in appointment_tools:
            tool_used = True
            break
    
    if not tool_used and is_appointment:
        return False, "Appointment scheduling detected but appropriate tools were not used"
    
    return True, "Appointment scheduling handled correctly"

# Define a setup function for testing
def setup_greeting_state():
    """Set up the greeting state for testing"""
    class GreetingStateContext:
        def __enter__(self):
            print("Setting up greeting state environment...")
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            print("Cleaning up greeting state environment...")
    
    return GreetingStateContext()

# Example usage of the llm_eval decorator with healthAgent
@llm_eval(
    rules=HEALTH_AGENT_RULES + [validate_appointment_scheduling],
    setup=setup_greeting_state,
    input_param="user_input"
)
def process_greeting(user_input: str) -> Dict:
    """Process a greeting using the healthAgent."""
    # Create a mock database for the state
    mock_db = MockDatabase()
    
    # Create a concrete state for testing
    state = LLMGreetingState(mock_db)
    
    # Process the input using the state's process_input_with_llm method
    messages = [
        {"role": "system", "content": state.system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    # Get tools for the greeting state
    tools = tool_manager.get_tools_for_state("GREETING")
    
    # Make LLM call
    response = llm_service.chat_completion(
        messages=messages,
        tools=tools,
        model=state.model
    )
    
    # Return the response
    return response

# Example for patient info collection
def setup_patient_info_state():
    """Set up the patient info collection state for testing"""
    print("Setting up patient info collection state...")
    return None

@llm_eval(
    rules=[
        "always extract patient name when provided",
        "always extract patient contact information when provided",
        "never ask for unnecessary personal information",
        "maintain appropriate professional tone"
    ],
    setup=setup_patient_info_state
)
def process_patient_info(user_input: str) -> Dict:
    """Process patient information using the healthAgent."""
    # Create a mock database for the state
    mock_db = MockDatabase()
    
    # For simplicity, we'll use the greeting state but with a different system prompt
    # In a real implementation, you would use the appropriate state class
    state = LLMGreetingState(mock_db)
    state.system_prompt = """You are HealthBot, an AI assistant for scheduling doctor appointments.

Current State: COLLECT_PATIENT_INFO - Gathering patient details

Your tasks:
1. Extract any patient info using extract_patient_info tool
2. Use generate_response tool with appropriate next steps

Decision logic:
- If no name collected yet: Ask for their name
- If name collected but no contact info: Ask for email or phone
- If both name and contact collected: Use next_action="transition" and next_state="COLLECT_APPOINTMENT_TYPE"

CRITICAL: Progress through the information collection systematically and transition when ready."""
    
    # Process the input using the state's process_input_with_llm method
    messages = [
        {"role": "system", "content": state.system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    # Get tools for the patient info state
    tools = tool_manager.get_tools_for_state("COLLECT_PATIENT_INFO")
    
    # Make LLM call
    response = llm_service.chat_completion(
        messages=messages,
        tools=tools,
        model=state.model
    )
    
    # Return the response
    return response

# Run the examples
if __name__ == "__main__":
    # Clear any previous traces
    clear_traces()
    
    print("\n=== Greeting Example ===")
    result = process_greeting("Hello, I'd like to schedule an appointment with Dr. Smith.")
    print(f"Response: {result.content}")
    print(f"Model: {result.model}")
    print(f"Tokens: {result.usage.get('total_tokens') if result.usage else 'N/A'}")
    
    print("\n=== Patient Info Example ===")
    result = process_patient_info("My name is John Doe and my email is john.doe@example.com.")
    print(f"Response: {result.content}")
    print(f"Model: {result.model}")
    print(f"Tokens: {result.usage.get('total_tokens') if result.usage else 'N/A'}")
    
    # Access the traces
    print("\n=== Evaluation Traces ===")
    traces = get_traces()
    for i, trace in enumerate(traces):
        print(f"\nTrace {i+1}:")
        print(f"  Function: {trace['function']}")
        print(f"  Model: {trace['model']}")
        print(f"  Response: {trace['response'][:50]}...")
        print(f"  Rule violations: {len(trace['rule_violations'])}")
        for violation in trace['rule_violations']:
            print(f"    - {violation['rule']}: {violation['message']}")
    
    # Generate a simple report
    print("\n=== Evaluation Report ===")
    print(f"Total traces: {len(traces)}")
    total_violations = sum(len(trace['rule_violations']) for trace in traces)
    print(f"Total rule violations: {total_violations}")
    print(f"Evaluation timestamp: {datetime.now().isoformat()}")
