#!/usr/bin/env python3
"""
Test suite for the Health Agent system
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.health_agent import HealthAgent
from models.database import MockDatabase
from models.appointment import AppointmentType
from state_machine.state_machine import StateMachine

class TestHealthAgent(unittest.TestCase):
    """Test cases for the Health Agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.agent = HealthAgent()
    
    def test_agent_initialization(self):
        """Test that the agent initializes properly"""
        self.assertIsNotNone(self.agent.database)
        self.assertIsNotNone(self.agent.state_machine)
        self.assertIsNotNone(self.agent.conversation_handler)
        self.assertTrue(self.agent.is_initialized)
    
    def test_start_conversation(self):
        """Test starting a conversation"""
        message = self.agent.start_conversation()
        self.assertIsNotNone(message)
        self.assertIn("HealthBot", message)
        self.assertTrue(self.agent.is_conversation_active())
    
    def test_conversation_flow(self):
        """Test basic conversation flow"""
        # Start conversation
        self.agent.start_conversation()
        
        # Test appointment scheduling intent
        response = self.agent.process_message("I need to schedule an appointment")
        self.assertIsNotNone(response)
        
        # Check state progression
        status = self.agent.get_conversation_status()
        self.assertEqual(status['status'], 'active')
    
    def test_get_available_doctors(self):
        """Test getting available doctors"""
        doctors = self.agent.get_available_doctors()
        self.assertIsInstance(doctors, list)
        self.assertGreater(len(doctors), 0)
        
        # Check doctor structure
        doctor = doctors[0]
        required_keys = ['id', 'name', 'specialty', 'available_days', 'available_hours']
        for key in required_keys:
            self.assertIn(key, doctor)
    
    def test_get_available_specialties(self):
        """Test getting available specialties"""
        specialties = self.agent.get_available_specialties()
        self.assertIsInstance(specialties, list)
        self.assertGreater(len(specialties), 0)
    
    def test_reset_conversation(self):
        """Test resetting conversation"""
        # Start and process some messages
        self.agent.start_conversation()
        self.agent.process_message("Hello")
        
        # Reset
        message = self.agent.reset_conversation()
        self.assertIsNotNone(message)
        
        # Check that state is reset
        status = self.agent.get_conversation_status()
        self.assertEqual(status['current_state'], 'GREETING')
    
    def test_database_stats(self):
        """Test getting database statistics"""
        stats = self.agent.get_database_stats()
        self.assertIsInstance(stats, dict)
        
        required_keys = ['total_doctors', 'total_patients', 'total_appointments', 
                        'available_specialties', 'active_doctors']
        for key in required_keys:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], int)

class TestMockDatabase(unittest.TestCase):
    """Test cases for the Mock Database"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.db = MockDatabase()
    
    def test_database_initialization(self):
        """Test database initializes with sample data"""
        self.assertGreater(len(self.db.doctors), 0)
        self.assertGreater(len(self.db.patients), 0)
    
    def test_get_doctors_by_specialty(self):
        """Test getting doctors by specialty"""
        # Get all specialties
        specialties = self.db.get_available_specialties()
        self.assertGreater(len(specialties), 0)
        
        # Test getting doctors for first specialty
        specialty = specialties[0]
        doctors = self.db.get_doctors_by_specialty(specialty)
        self.assertIsInstance(doctors, list)
        
        # All returned doctors should have the requested specialty
        for doctor in doctors:
            self.assertEqual(doctor.specialty, specialty)
    
    def test_create_patient(self):
        """Test creating a new patient"""
        initial_count = len(self.db.patients)
        
        patient = self.db.create_patient(
            name="Test Patient",
            email="test@example.com",
            phone="(555) 123-4567"
        )
        
        self.assertIsNotNone(patient)
        self.assertEqual(patient.name, "Test Patient")
        self.assertEqual(len(self.db.patients), initial_count + 1)
    
    def test_check_doctor_availability(self):
        """Test checking doctor availability"""
        # Get a doctor
        doctors = list(self.db.doctors.values())
        doctor = doctors[0]
        
        # Test availability for next Monday at 10 AM
        next_monday = datetime.now() + timedelta(days=(7 - datetime.now().weekday()))
        appointment_time = next_monday.replace(hour=10, minute=0, second=0, microsecond=0)
        
        if 'Monday' in doctor.available_days:
            available = self.db.check_doctor_availability(doctor.id, appointment_time)
            self.assertIsInstance(available, bool)
    
    def test_create_appointment(self):
        """Test creating an appointment"""
        # Get a doctor and patient
        doctor = list(self.db.doctors.values())[0]
        patient = list(self.db.patients.values())[0]
        
        # Create appointment for next week
        appointment_time = datetime.now() + timedelta(days=7)
        appointment_time = appointment_time.replace(hour=10, minute=0, second=0, microsecond=0)
        
        appointment = self.db.create_appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_datetime=appointment_time,
            appointment_type=AppointmentType.CONSULTATION
        )
        
        if appointment:  # Only test if appointment was successfully created
            self.assertIsNotNone(appointment)
            self.assertEqual(appointment.patient_id, patient.id)
            self.assertEqual(appointment.doctor_id, doctor.id)

class TestStateMachine(unittest.TestCase):
    """Test cases for the State Machine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.sm = StateMachine()
        # We'll use a simple mock state for testing
        from state_machine.base_state import BaseState, StateResult
        
        class MockState(BaseState):
            def enter(self, context):
                return "Mock state entered"
            
            def process_input(self, user_input, context):
                if user_input.lower() == "next":
                    return StateResult.TRANSITION, "NEXT_STATE", context
                return StateResult.CONTINUE, None, context
        
        self.mock_state = MockState("MOCK_STATE")
        self.sm.add_state(self.mock_state)
    
    def test_add_state(self):
        """Test adding states to state machine"""
        self.assertIn("MOCK_STATE", self.sm.states)
        self.assertEqual(self.sm.states["MOCK_STATE"], self.mock_state)
    
    def test_set_initial_state(self):
        """Test setting initial state"""
        self.sm.set_initial_state("MOCK_STATE")
        self.assertEqual(self.sm.current_state, self.mock_state)
    
    def test_start_conversation(self):
        """Test starting conversation"""
        self.sm.set_initial_state("MOCK_STATE")
        message = self.sm.start_conversation()
        self.assertEqual(message, "Mock state entered")
        self.assertIn('conversation_started', self.sm.context)
    
    def test_reset(self):
        """Test resetting state machine"""
        self.sm.set_initial_state("MOCK_STATE")
        self.sm.start_conversation()
        self.sm.process_user_input("hello")
        
        # Reset
        self.sm.reset()
        
        self.assertIsNone(self.sm.current_state)
        self.assertEqual(len(self.sm.context), 0)
        self.assertEqual(len(self.sm.conversation_history), 0)
        self.assertFalse(self.sm.is_complete)

def run_example_conversation():
    """Run an example conversation to demonstrate the system"""
    print("\n" + "="*60)
    print("🧪 RUNNING EXAMPLE CONVERSATION")
    print("="*60)
    
    agent = HealthAgent()
    
    # Start conversation
    print("🤖 Starting conversation...")
    message = agent.start_conversation()
    print(f"Agent: {message}")
    
    # Simulate user responses
    test_inputs = [
        "I need to schedule an appointment",
        "John Doe",
        "john.doe@email.com",
        "consultation",
        "cardiology",
        "tomorrow at 2pm"
    ]
    
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n👤 User ({i}): {user_input}")
        try:
            response = agent.process_message(user_input)
            print(f"🤖 Agent: {response}")
            
            # Show current state
            status = agent.get_conversation_status()
            print(f"   [State: {status['current_state']}]")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    print(f"\n📊 Final Status: {agent.get_conversation_status()}")
    print("="*60)

if __name__ == "__main__":
    # Run tests
    print("Running Health Agent Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run example conversation
    run_example_conversation()
