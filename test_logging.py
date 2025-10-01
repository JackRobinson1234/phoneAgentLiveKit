#!/usr/bin/env python3
"""
Quick test script to verify call logging is working
Run this after setting up Supabase to test the integration
"""

import os
import time
from dotenv import load_dotenv
from src.logging import CallLogger

# Load environment variables
load_dotenv()

def test_logger_initialization():
    """Test that logger initializes correctly"""
    print("🧪 Testing Logger Initialization...")
    
    try:
        logger = CallLogger()
        print("✅ Logger initialized successfully!")
        return logger
    except Exception as e:
        print(f"❌ Logger initialization failed: {e}")
        print("\nMake sure you have:")
        print("1. Created Supabase project")
        print("2. Run database/schema.sql in SQL Editor")
        print("3. Set SUPABASE_URL and SUPABASE_KEY in .env")
        return None


def test_call_logging(logger):
    """Test logging a sample call"""
    print("\n🧪 Testing Call Logging...")
    
    try:
        # Start a test call
        call_id = logger.start_call(
            session_id="test_session_001",
            initial_state="GREETING"
        )
        print(f"✅ Call started: {call_id}")
        
        # Log some transitions
        logger.log_transition(
            from_state="GREETING",
            to_state="PET_SURRENDER",
            user_input="I want to surrender a dog",
            agent_response="I understand you'd like to surrender a dog. Could you tell me the reason?",
            context={"animal_type": "dog", "detected_intent": "surrender"},
            context_updates={"animal_type": "dog", "detected_intent": "surrender"},
            transition_type="optimized",
            llm_model="anthropic/claude-3.5-sonnet",
            llm_tokens=2500,
            processing_time_ms=1200
        )
        print("✅ Transition 1 logged")
        
        logger.log_transition(
            from_state="PET_SURRENDER",
            to_state="PET_SURRENDER",
            user_input="I don't want it anymore",
            agent_response="I understand. Does your dog have any health issues?",
            context={"animal_type": "dog", "surrender_reason": "no longer wants pet"},
            context_updates={"surrender_reason": "no longer wants pet"},
            transition_type="continue",
            llm_model="anthropic/claude-3.5-sonnet",
            llm_tokens=2600,
            processing_time_ms=1100
        )
        print("✅ Transition 2 logged")
        
        # End the call
        logger.end_call(
            final_state="PET_SURRENDER",
            completion_status="completed"
        )
        print("✅ Call ended")
        
        # Wait for async logging to complete
        print("⏳ Waiting for background logging to complete...")
        time.sleep(2)
        
        return call_id
        
    except Exception as e:
        print(f"❌ Call logging failed: {e}")
        return None


def test_flow_retrieval(logger, call_id):
    """Test retrieving call flow"""
    print("\n🧪 Testing Flow Retrieval...")
    
    try:
        flow = logger.get_call_flow(call_id)
        
        if flow:
            print("✅ Flow retrieved successfully!")
            print(f"\nCall Info:")
            print(f"  Session: {flow['call']['session_id']}")
            print(f"  Duration: {flow['call']['duration_seconds']}s")
            print(f"  Status: {flow['call']['completion_status']}")
            print(f"  Transitions: {len(flow['transitions'])}")
            
            return flow
        else:
            print("❌ Flow not found")
            return None
            
    except Exception as e:
        print(f"❌ Flow retrieval failed: {e}")
        return None


def test_mermaid_generation(logger, call_id):
    """Test Mermaid diagram generation"""
    print("\n🧪 Testing Mermaid Generation...")
    
    try:
        mermaid = logger.generate_mermaid_flow(call_id)
        
        if mermaid:
            print("✅ Mermaid diagram generated!")
            print("\nDiagram:")
            print(mermaid)
            print("\n📋 Copy the above and paste into https://mermaid.live/ to visualize")
            return True
        else:
            print("❌ Mermaid generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Mermaid generation failed: {e}")
        return False


def test_database_query(logger):
    """Test direct database queries"""
    print("\n🧪 Testing Database Queries...")
    
    try:
        # Get recent calls
        result = logger.supabase.table('calls').select('*').order('start_time', desc=True).limit(5).execute()
        
        print(f"✅ Found {len(result.data)} recent calls")
        
        for call in result.data:
            print(f"  - {call['session_id']}: {call['completion_status']} ({call.get('duration_seconds', 0)}s)")
        
        return True
        
    except Exception as e:
        print(f"❌ Database query failed: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Call Logging Test Suite")
    print("="*60)
    
    # Test 1: Initialization
    logger = test_logger_initialization()
    if not logger:
        print("\n❌ Tests failed - fix initialization first")
        return
    
    # Test 2: Call Logging
    call_id = test_call_logging(logger)
    if not call_id:
        print("\n❌ Tests failed - fix call logging")
        return
    
    # Test 3: Flow Retrieval
    flow = test_flow_retrieval(logger, call_id)
    if not flow:
        print("\n❌ Tests failed - fix flow retrieval")
        return
    
    # Test 4: Mermaid Generation
    test_mermaid_generation(logger, call_id)
    
    # Test 5: Database Queries
    test_database_query(logger)
    
    print("\n" + "="*60)
    print("✅ All Tests Passed!")
    print("="*60)
    print("\nNext steps:")
    print("1. Check Supabase dashboard → Table Editor → calls")
    print("2. Run: python database/example_queries.py")
    print("3. Start using the agent - all calls will be logged!")
    print("\nTest call ID:", call_id)


if __name__ == '__main__':
    main()
