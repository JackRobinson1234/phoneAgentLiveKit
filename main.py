#!/usr/bin/env python3
"""
Health Agent - AI Doctor Appointment Scheduler
Main application entry point for the health agent system.
"""

import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.llm_health_agent import LLMHealthAgent
from config.settings import AGENT_CONFIG

class HealthAgentCLI:
    """Command-line interface for the Health Agent"""
    
    def __init__(self):
        self.agent = LLMHealthAgent()
        self.running = False
    
    def display_welcome(self):
        """Display welcome message and instructions"""
        print("=" * 60)
        print("🏥 HEALTH AGENT - AI Doctor Appointment Scheduler")
        print("=" * 60)
        print("Welcome! I'm your AI assistant for scheduling doctor appointments.")
        print("\nCommands:")
        print("  • Type your messages naturally")
        print("  • 'help' - Show available commands")
        print("  • 'status' - Show conversation status")
        print("  • 'doctors' - List available doctors")
        print("  • 'llm-test' - Test LLM integration")
        print("  • 'reset' - Start a new conversation")
        print("  • 'quit' or 'exit' - End the session")
        print("-" * 60)
    
    def display_help(self):
        """Display help information"""
        print("\n📋 HELP - Available Commands:")
        print("  help          - Show this help message")
        print("  status        - Show current conversation status")
        print("  doctors       - List all available doctors")
        print("  specialties   - List available medical specialties")
        print("  stats         - Show database statistics")
        print("  history       - Show conversation history")
        print("  appointment   - Show current appointment details")
        print("  reset         - Start a new conversation")
        print("  quit/exit     - End the session")
        print("\n💬 Natural Language:")
        print("  You can also interact naturally, for example:")
        print("  • 'I need to schedule an appointment'")
        print("  • 'Book me with a cardiologist'")
        print("  • 'I want to see Dr. Johnson tomorrow'")
        print()
    
    def handle_command(self, user_input: str) -> bool:
        """
        Handle special commands
        
        Returns:
            True if command was handled, False if should be processed as normal input
        """
        command = user_input.lower().strip()
        
        if command in ['quit', 'exit', 'bye', 'goodbye']:
            response = self.agent.end_conversation()
            print(f"\n🤖 {response}")
            return True
        
        elif command == 'help':
            self.display_help()
            return True
        
        elif command == 'llm-test':
            print("\n🧪 Testing LLM Integration...")
            results = self.agent.test_llm_integration()
            print(f"  LLM Service Available: {'✅' if results['llm_service_available'] else '❌'}")
            print(f"  Connection Test: {'✅' if results['connection_test'] else '❌'}")
            print(f"  NLP Processor: {'✅' if results['nlp_processor_working'] else '❌'}")
            if results.get('sample_analysis'):
                analysis = results['sample_analysis']
                print(f"  Sample Analysis:")
                print(f"    Intent: {analysis.get('intent')}")
                print(f"    Confidence: {analysis.get('confidence', 0):.2f}")
                print(f"    Specialty: {analysis.get('specialty', 'None')}")
                print(f"    Method: {analysis.get('method')}")
            if results.get('error'):
                print(f"  Error: {results['error']}")
            return True
        
        elif command == 'status':
            status = self.agent.get_conversation_status()
            print(f"\n📊 Conversation Status:")
            print(f"  Status: {status['status'].title()}")
            if status['status'] != 'not_started':
                print(f"  Current State: {status['current_state']}")
                print(f"  Turn Count: {status['turn_count']}")
            return True
        
        elif command == 'doctors':
            doctors = self.agent.get_available_doctors()
            print(f"\n👨‍⚕️ Available Doctors ({len(doctors)}):")
            for doctor in doctors:
                days = ", ".join(doctor['available_days'])
                hours = f"{doctor['available_hours']['start']}-{doctor['available_hours']['end']}"
                print(f"  • {doctor['name']} - {doctor['specialty']}")
                print(f"    Available: {days} ({hours})")
            return True
        
        elif command == 'specialties':
            specialties = self.agent.get_available_specialties()
            print(f"\n🏥 Available Specialties ({len(specialties)}):")
            for specialty in specialties:
                print(f"  • {specialty}")
            return True
        
        elif command == 'stats':
            stats = self.agent.get_database_stats()
            print(f"\n📈 Database Statistics:")
            print(f"  Total Doctors: {stats['total_doctors']}")
            print(f"  Active Doctors: {stats['active_doctors']}")
            print(f"  Total Patients: {stats['total_patients']}")
            print(f"  Total Appointments: {stats['total_appointments']}")
            print(f"  Available Specialties: {stats['available_specialties']}")
            print(f"  LLM Enhanced: {stats.get('llm_enabled', False)}")
            if stats.get('llm_connection_test') is not None:
                print(f"  LLM Connection: {'✅' if stats['llm_connection_test'] else '❌'}")
            return True
        
        elif command == 'history':
            history = self.agent.get_conversation_history()
            if not history:
                print("\n📝 No conversation history available.")
            else:
                print(f"\n📝 Conversation History ({len(history)} messages):")
                for entry in history[-10:]:  # Show last 10 messages
                    timestamp = entry['timestamp'].strftime("%H:%M:%S")
                    speaker = entry['speaker']
                    message = entry['message'][:100] + "..." if len(entry['message']) > 100 else entry['message']
                    print(f"  [{timestamp}] {speaker}: {message}")
            return True
        
        elif command == 'appointment':
            appointment = self.agent.get_appointment_summary()
            if not appointment:
                print("\n📅 No appointment scheduled yet.")
            else:
                print(f"\n📅 Current Appointment:")
                print(f"  ID: {appointment['appointment_id']}")
                print(f"  Patient: {appointment['patient_name']}")
                print(f"  Doctor: {appointment['doctor_name']} ({appointment['specialty']})")
                print(f"  Date & Time: {appointment['appointment_datetime']}")
                print(f"  Type: {appointment['appointment_type']}")
                print(f"  Status: {appointment['status']}")
            return True
        
        elif command == 'reset':
            response = self.agent.reset_conversation()
            print(f"\n🔄 Conversation reset.")
            print(f"🤖 {response}")
            return True
        
        return False
    
    def run(self):
        """Run the main CLI loop"""
        self.display_welcome()
        
        try:
            # Start the conversation
            initial_message = self.agent.start_conversation()
            print(f"\n🤖 {initial_message}")
            
            self.running = True
            
            while self.running:
                try:
                    # Get user input
                    user_input = input("\n👤 You: ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Check if it's a command
                    if self.handle_command(user_input):
                        if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                            self.running = False
                        continue
                    
                    # Process through the agent
                    response = self.agent.process_message(user_input)
                    print(f"\n🤖 {response}")
                    
                    # Check if conversation is complete
                    if self.agent.get_conversation_status()['status'] == 'completed':
                        print("\n✅ Conversation completed successfully!")
                        
                        # Ask if user wants to start a new conversation
                        while True:
                            continue_input = input("\nWould you like to start a new conversation? (y/n): ").lower().strip()
                            if continue_input in ['y', 'yes']:
                                response = self.agent.reset_conversation()
                                print(f"\n🤖 {response}")
                                break
                            elif continue_input in ['n', 'no']:
                                self.running = False
                                break
                            else:
                                print("Please enter 'y' for yes or 'n' for no.")
                
                except KeyboardInterrupt:
                    print("\n\n⚠️  Interrupted by user.")
                    confirm = input("Are you sure you want to quit? (y/n): ").lower().strip()
                    if confirm in ['y', 'yes']:
                        self.running = False
                    else:
                        print("Continuing conversation...")
                
                except Exception as e:
                    print(f"\n❌ An error occurred: {str(e)}")
                    print("Type 'reset' to start over or 'quit' to exit.")
        
        except Exception as e:
            print(f"\n❌ Failed to start Health Agent: {str(e)}")
            print("Please check your installation and try again.")
        
        finally:
            print("\n👋 Thank you for using Health Agent! Goodbye!")

def main():
    """Main entry point"""
    try:
        cli = HealthAgentCLI()
        cli.run()
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()