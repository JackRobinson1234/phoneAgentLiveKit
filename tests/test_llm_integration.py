#!/usr/bin/env python3
"""
Test suite for LLM integration in the Health Agent system
"""

import unittest
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.llm_health_agent import LLMHealthAgent
from agents.llm_service import llm_service, tool_manager
from agents.llm_nlp_processor import LLMNLPProcessor

class TestLLMIntegration(unittest.TestCase):
    """Test cases for LLM integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Skip tests if no API key is available
        if not os.getenv('OPENROUTER_API_KEY'):
            self.skipTest("OPENROUTER_API_KEY not set - skipping LLM tests")
        
        self.agent = LLMHealthAgent()
        self.nlp_processor = LLMNLPProcessor()
    
    def test_llm_service_initialization(self):
        """Test LLM service initializes correctly"""
        self.assertTrue(hasattr(llm_service, 'client'))
        self.assertIsNotNone(llm_service.api_key)
    
    def test_tool_manager_initialization(self):
        """Test tool manager has required tools"""
        required_tools = [
            'extract_patient_info',
            'analyze_appointment_request', 
            'parse_datetime_request',
            'generate_response'
        ]
        
        for tool_name in required_tools:
            self.assertIsNotNone(tool_manager.get_tool(tool_name))
    
    def test_llm_connection(self):
        """Test connection to OpenRouter"""
        try:
            connection_works = llm_service.test_connection()
            self.assertTrue(connection_works, "LLM connection test failed")
        except Exception as e:
            self.skipTest(f"LLM connection failed: {e}")
    
    def test_nlp_processor_with_llm(self):
        """Test NLP processor using LLM"""
        test_inputs = [
            "I need to schedule an appointment",
            "Book me with a cardiologist",
            "My name is John Smith",
            "john.smith@email.com",
            "Tomorrow at 2pm"
        ]
        
        for input_text in test_inputs:
            with self.subTest(input=input_text):
                result = self.nlp_processor.process_input(input_text)
                
                # Should have basic structure
                self.assertIn('intent', result)
                self.assertIn('confidence', result)
                self.assertIn('raw_text', result)
                
                # Should use LLM method if available
                if result.get('method') == 'llm':
                    self.assertGreater(result['confidence'], 0)
    
    def test_agent_llm_enhancement(self):
        """Test that agent uses LLM enhancement"""
        if not self.agent.llm_enabled:
            self.skipTest("LLM not enabled in agent")
        
        # Start conversation
        self.agent.start_conversation()
        
        # Test processing with LLM
        response = self.agent.process_message("I need to see a heart doctor")
        
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        
        # Check status includes LLM info
        status = self.agent.get_conversation_status()
        self.assertTrue(status.get('llm_enabled', False))
    
    def test_llm_diagnostics(self):
        """Test LLM diagnostic functionality"""
        diagnostics = self.agent.test_llm_integration()
        
        # Should have diagnostic keys
        required_keys = [
            'llm_service_available',
            'nlp_processor_working', 
            'connection_test',
            'sample_analysis'
        ]
        
        for key in required_keys:
            self.assertIn(key, diagnostics)

def run_llm_conversation_example():
    """Run an example conversation with LLM enhancement"""
    print("\n" + "="*60)
    print("🤖 RUNNING LLM-ENHANCED CONVERSATION EXAMPLE")
    print("="*60)
    
    # Check for API key
    if not os.getenv('OPENROUTER_API_KEY'):
        print("❌ OPENROUTER_API_KEY not set. Please set it to test LLM features.")
        print("   Example: export OPENROUTER_API_KEY='your_key_here'")
        return
    
    agent = LLMHealthAgent()
    
    # Test LLM integration first
    print("🧪 Testing LLM Integration...")
    results = agent.test_llm_integration()
    
    if not results['connection_test']:
        print("❌ LLM connection failed. Running in fallback mode.")
        if results.get('error'):
            print(f"   Error: {results['error']}")
    else:
        print("✅ LLM integration working!")
    
    # Start conversation
    print("\n🤖 Starting LLM-enhanced conversation...")
    message = agent.start_conversation()
    print(f"Agent: {message}")
    
    # Simulate natural language inputs
    test_inputs = [
        "Hi, I need to book an appointment with a heart specialist",
        "My name is Sarah Johnson and my email is sarah.j@email.com", 
        "I need a consultation for chest pain",
        "I prefer cardiology",
        "How about next Monday afternoon?"
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n👤 User ({i}): {user_input}")
        try:
            response = agent.process_message(user_input)
            print(f"🤖 Agent: {response}")
            
            # Show enhanced status
            status = agent.get_conversation_status()
            llm_info = ""
            if status.get('llm_enabled'):
                llm_info = " [LLM Enhanced]"
            print(f"   [State: {status['current_state']}{llm_info}]")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    print(f"\n📊 Final Status: {agent.get_conversation_status()}")
    print("="*60)

if __name__ == "__main__":
    # Run tests
    print("Running LLM Integration Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run example conversation
    run_llm_conversation_example()
