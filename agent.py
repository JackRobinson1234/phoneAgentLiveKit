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
        
        # Initialize the LiveKit Agent with a placeholder LLM
        # We override llm_node to use our state machine instead
        super().__init__(
            instructions=initial_greeting,
            # We need to provide an LLM for LiveKit to call llm_node
            # But we'll override it with our state machine
        )
    
    async def llm_node(
        self,
        chat_ctx,  # llm.ChatContext
        tools,     # list[FunctionTool | RawFunctionTool]
        model_settings,  # ModelSettings
    ):
        """
        Override the LLM node to use our state machine instead of OpenAI.
        This is called automatically when the user finishes speaking.
        
        Args:
            chat_ctx: The conversation context with message history
            tools: Available function tools (we don't use these)
            model_settings: Model configuration (we don't use this)
            
        Yields:
            str: Response text from our state machine
        """
        import asyncio
        import traceback
        
        try:
            # Get the last user message from the chat context
            # ChatContext uses 'items' not 'messages'
            user_input = ""
            if hasattr(chat_ctx, 'items') and chat_ctx.items:
                last_message = chat_ctx.items[-1]
                # Handle different message formats
                if hasattr(last_message, 'content'):
                    if isinstance(last_message.content, list):
                        # Content is a list of content parts
                        user_input = " ".join(str(part) for part in last_message.content)
                    else:
                        user_input = str(last_message.content)
                else:
                    user_input = str(last_message)
            
            print(f"🎤 User said: {user_input}")
            
            # Process through our state machine with timeout
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    self.animal_control_agent.process_message, 
                    user_input
                ),
                timeout=30.0  # 30 second timeout
            )
            
            print(f"🤖 Agent responding: {response[:100]}...")
            
            # Yield the response (LiveKit expects an async generator)
            yield response
            
        except asyncio.TimeoutError:
            print(f"⏱️ Timeout processing message: {user_input}")
            yield "I'm sorry, that's taking longer than expected. Could you please repeat that?"
        except Exception as e:
            print(f"❌ Error in llm_node: {e}")
            traceback.print_exc()
            yield "I apologize, but I encountered an error. Could you please try again?"


async def entrypoint(ctx: agents.JobContext):
    """
    Main entrypoint for the LiveKit agent
    
    This function is called when a participant joins a room
    """
    
    # Create the agent session with STT-LLM-TTS pipeline
    # We provide a minimal LLM so LiveKit calls llm_node, but we override it
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            language="multi"  # Supports multiple languages
        ),
        llm=openai.LLM(model="gpt-4o-mini"),  # Placeholder - overridden by llm_node
        tts=cartesia.TTS(
            model="sonic-2",
            voice="f786b574-daa5-4673-aa0c-cbe3e8534c02"  # Default voice
        ),
        vad=silero.VAD.load(),  # Voice Activity Detection
        turn_detection=MultilingualModel(),  # Detect when user finishes speaking
    )

    # Create our agent instance
    agent = AnimalControlVoiceAssistant()
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            # Use BVCTelephony for phone calls (optimized for telephony audio)
            noise_cancellation=noise_cancellation.BVCTelephony(),
        ),
    )

    # Speak the initial greeting from our state machine
    # (The greeting was already generated when we initialized the agent)
    session.say(agent.instructions)


if __name__ == "__main__":
    # Run the agent with LiveKit CLI
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
