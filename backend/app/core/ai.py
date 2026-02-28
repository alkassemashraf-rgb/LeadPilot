from typing import List, Dict, Optional
import google.generativeai as genai
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AIProvider:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.genai_client = genai
        else:
            self.genai_client = None

    async def generate_chat_reply(
        self, 
        prompt: str, 
        history: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = None # Ignored, here for signature compatibility
    ) -> str:
        """
        Unified Gemini-only chat generation.
        prompt: System instructions.
        history: List of {"role": "user"|"assistant", "content": "..."}
        """
        if not self.genai_client:
            return "Gemini API Key not configured."

        try:
            # Initialize model with system instructions
            model_instance = self.genai_client.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=prompt
            )

            # Convert history to Gemini format
            # Gemini roles: 'user', 'model'
            gemini_history = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg["content"]]})

            last_message_content = "Please respond based on the conversation."
            if gemini_history and gemini_history[-1]["role"] == "user":
                last_user_msg = gemini_history.pop()
                last_message_content = last_user_msg["parts"][0]
                # Re-start chat without the last user msg
                chat = model_instance.start_chat(history=gemini_history)
            else:
                # Start chat with current history
                chat = model_instance.start_chat(history=gemini_history)

            # Use settings defaults if not provided
            calc_temp = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE
            calc_tokens = max_tokens if max_tokens is not None else settings.DEFAULT_MAX_OUTPUT_TOKENS

            response = await chat.send_message_async(
                last_message_content,
                generation_config=genai.types.GenerationConfig(
                    temperature=calc_temp,
                    max_output_tokens=calc_tokens
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini Generation Error: {str(e)}")
            return f"AI Error: {str(e)}"

    # For runtime.py compatibility
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Helper for runtime.py which sends a combined list with system message first."""
        system_msg = next((m for m in messages if m["role"] == "system"), None)
        prompt = system_msg["content"] if system_msg else "You are a helpful assistant."
        
        history = [m for m in messages if m["role"] != "system"]
        return await self.generate_chat_reply(prompt, history, temperature, max_tokens)

ai_provider = AIProvider()
