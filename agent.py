#!/usr/bin/env python3
"""
LiveKit Voice Agent for Animal Control Services
Integrates with existing LLMAnimalControlAgent for conversation logic
"""

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Import our existing animal control agent
from src.agents.llm_animal_control_agent import LLMAnimalControlAgent

# Load environment variables from .env.local (LiveKit standard) or .env
load_dotenv(".env.local")
load_dotenv(".env")


class AnimalControlVoiceAssistant(Agent):
    """Voice assistant that wraps our existing Animal Control Agent"""
    
    def __init__(self) -> None:
        # Initialize the existing animal control agent
        self.animal_control_agent = LLMAnimalControlAgent()
        
        # Get the initial greeting from our agent
        initial_greeting = self.animal_control_agent.start_conversation()
        
        # Initialize the LiveKit Agent with our custom instructions
        super().__init__(
            instructions=f"""You are a helpful voice AI assistant for Animal Control Services.
            
Your role is to help people with:
- Reporting injured, abused, or emergency animal cases
- Reporting found stray animals
- Reporting lost pets
- Scheduling pet surrenders
- Providing general animal control information

Be professional, empathetic, and efficient. Ask clarifying questions when needed.
Collect necessary information like location, animal description, and contact details.

{initial_greeting}"""
        )
    
    async def on_message(self, message: str) -> str:
        """
        Process incoming voice messages through our Animal Control Agent
        
        Args:
            message: Transcribed user speech
            
        Returns:
            Agent's response to be spoken back
        """
        try:
            # Process the message through our existing agent
            response = self.animal_control_agent.process_message(message)
            return response
        except Exception as e:
            print(f"Error processing message: {e}")
            return "I apologize, but I encountered an error processing your request. Could you please try again?"


async def entrypoint(ctx: agents.JobContext):
    """
    Main entrypoint for the LiveKit agent
    
    This function is called when a participant joins a room
    """
    
    # Create the agent session with STT-LLM-TTS pipeline
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi"  # Supports multiple languages
        ),
        llm=openai.LLM(
            model="gpt-4o-mini"  # Fast and cost-effective
        ),
        tts=cartesia.TTS(
            model="sonic-2",
            voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"  # Default voice
        ),
        vad=silero.VAD.load(),  # Voice Activity Detection
        turn_detection=MultilingualModel(),  # Detect when user finishes speaking
    )

    # Start the session
    await session.start(
        room=ctx.room,
        agent=AnimalControlVoiceAssistant(),
        room_input_options=RoomInputOptions(
            # Use BVCTelephony for phone calls (optimized for telephony audio)
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )

    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and ask how you can help them with animal control services today."
    )


if __name__ == "__main__":
    # Run the agent with LiveKit CLI
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
