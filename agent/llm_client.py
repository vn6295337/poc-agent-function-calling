"""
LLM client with function calling support using Gemini and Groq.
Adapted from poc-rag pattern: Gemini -> Groq -> OpenRouter fallback.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False
    logger.warning("requests not available, using urllib")


def _http_post(url: str, headers: dict, payload: dict, timeout: int = 60):
    """HTTP POST helper."""
    if _HAS_REQUESTS:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    else:
        import urllib.request as _urllib_request
        data = json.dumps(payload).encode("utf-8")
        req = _urllib_request.Request(url, data=data, headers=headers, method="POST")
        with _urllib_request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))


class LLMClient:
    """
    LLM client supporting function calling with Gemini, Groq, OpenRouter.
    Uses provider cascade: Gemini -> Groq -> OpenRouter -> Fallback
    """

    def __init__(self):
        """Initialize LLM client with available providers."""
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")

        # Model names
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")

        # Determine active provider (priority order)
        if self.gemini_key:
            self.provider = "gemini"
            logger.info(f"Primary provider: Gemini ({self.gemini_model})")
        elif self.groq_key:
            self.provider = "groq"
            logger.info(f"Primary provider: Groq ({self.groq_model})")
        elif self.openrouter_key:
            self.provider = "openrouter"
            logger.info(f"Primary provider: OpenRouter ({self.openrouter_model})")
        else:
            raise RuntimeError("No LLM API key found. Set GEMINI_API_KEY, GROQ_API_KEY, or OPENROUTER_API_KEY")

    def call_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        max_iterations: int = 5
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Call LLM with function calling support.

        Args:
            messages: Conversation messages
            functions: Function definitions
            max_iterations: Max function calling iterations

        Returns:
            Tuple of (final_response, function_calls_log)
        """
        # Try providers in cascade order
        errors = []

        # Try Gemini first (supports function calling)
        if self.gemini_key:
            try:
                return self._call_gemini_with_functions(messages, functions, max_iterations)
            except Exception as e:
                logger.warning(f"Gemini failed: {e}")
                errors.append(f"gemini: {e}")

        # Try Groq second (OpenAI-compatible, supports function calling)
        if self.groq_key:
            try:
                return self._call_groq_with_functions(messages, functions, max_iterations)
            except Exception as e:
                logger.warning(f"Groq failed: {e}")
                errors.append(f"groq: {e}")

        # Try OpenRouter third (some models support function calling)
        if self.openrouter_key:
            try:
                return self._call_openrouter_with_functions(messages, functions, max_iterations)
            except Exception as e:
                logger.warning(f"OpenRouter failed: {e}")
                errors.append(f"openrouter: {e}")

        # All failed
        raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")

    def _call_gemini_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        max_iterations: int
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """Gemini function calling implementation."""
        function_calls_log = []

        # Convert functions to Gemini format
        tools = self._convert_to_gemini_tools(functions)

        # Build Gemini request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent?key={self.gemini_key}"

        # Extract system message and user content
        system_instruction = ""
        user_content = ""

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                user_content = msg["content"]

        payload = {
            "contents": [{"parts": [{"text": user_content}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]} if system_instruction else None,
            "tools": tools,
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 2048
            }
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        headers = {"Content-Type": "application/json"}

        logger.info(f"Calling Gemini API")
        response = _http_post(url, headers, payload)

        # Parse response for function calls
        if "candidates" in response and len(response["candidates"]) > 0:
            candidate = response["candidates"][0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            # Check for function call
            for part in parts:
                if "functionCall" in part:
                    function_call = part["functionCall"]
                    function_name = function_call.get("name")
                    function_args = function_call.get("args", {})

                    logger.info(f"Gemini requested function: {function_name}")

                    function_calls_log.append({
                        "iteration": 1,
                        "function": function_name,
                        "arguments": function_args,
                        "status": "pending"
                    })

                    # Return None to indicate function call needed
                    return None, function_calls_log

                elif "text" in part:
                    # Final text response
                    return part["text"], function_calls_log

        # No function call and no text - error
        logger.error(f"Unexpected Gemini response: {response}")
        raise RuntimeError(f"Gemini returned unexpected response format")

    def _call_groq_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        max_iterations: int
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """Groq function calling (OpenAI-compatible API with tools format)."""
        function_calls_log = []

        url = "https://api.groq.com/openai/v1/chat/completions"

        # Convert functions to tools format (OpenAI's new format)
        tools = [{"type": "function", "function": func} for func in functions]

        payload = {
            "model": self.groq_model,
            "messages": messages,
            "tools": tools,
            "temperature": 0.0,
            "max_tokens": 2048
        }

        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Calling Groq API")
        response = _http_post(url, headers, payload)

        # Parse OpenAI-style response
        if "choices" in response and len(response["choices"]) > 0:
            message = response["choices"][0].get("message", {})

            # Check for tool_calls (new format)
            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0]  # Get first tool call
                function_call = tool_call.get("function", {})
                function_name = function_call.get("name")
                function_args_str = function_call.get("arguments", "{}")
                function_args = json.loads(function_args_str)

                logger.info(f"Groq requested function: {function_name}")

                function_calls_log.append({
                    "iteration": 1,
                    "function": function_name,
                    "arguments": function_args,
                    "tool_call_id": tool_call.get("id"),
                    "status": "pending"
                })

                return None, function_calls_log

            elif "content" in message and message["content"]:
                # Final text response
                return message["content"], function_calls_log

        logger.error(f"Unexpected Groq response: {response}")
        raise RuntimeError(f"Groq returned unexpected response format")

    def _call_openrouter_with_functions(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        max_iterations: int
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """OpenRouter function calling (OpenAI-compatible with tools format)."""
        function_calls_log = []

        url = "https://openrouter.ai/api/v1/chat/completions"

        # Convert to tools format
        tools = [{"type": "function", "function": func} for func in functions]

        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "tools": tools,
            "temperature": 0.0,
            "max_tokens": 2048
        }

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"Calling OpenRouter API")
        response = _http_post(url, headers, payload)

        # Parse response
        if "choices" in response and len(response["choices"]) > 0:
            message = response["choices"][0].get("message", {})

            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0]
                function_call = tool_call.get("function", {})
                function_name = function_call.get("name")
                function_args_str = function_call.get("arguments", "{}")
                function_args = json.loads(function_args_str)

                logger.info(f"OpenRouter requested function: {function_name}")

                function_calls_log.append({
                    "iteration": 1,
                    "function": function_name,
                    "arguments": function_args,
                    "tool_call_id": tool_call.get("id"),
                    "status": "pending"
                })

                return None, function_calls_log

            elif "content" in message and message["content"]:
                return message["content"], function_calls_log

        logger.error(f"Unexpected OpenRouter response: {response}")
        raise RuntimeError(f"OpenRouter returned unexpected response format")

    def continue_with_function_result(
        self,
        messages: List[Dict[str, str]],
        function_name: str,
        function_result: Dict[str, Any],
        functions: List[Dict[str, Any]],
        tool_use_id: Optional[str] = None
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Continue conversation after function execution.

        Args:
            messages: Current conversation
            function_name: Executed function name
            function_result: Function result
            functions: Function definitions
            tool_use_id: Tool use ID (not used for Gemini/Groq)

        Returns:
            Tuple of (response, function_calls_log)
        """
        # Add function result to messages
        current_messages = messages.copy()

        # For Gemini, we need different format
        if self.provider == "gemini" and self.gemini_key:
            # Gemini requires function response in specific format
            # For simplicity, we'll add it as a user message
            current_messages.append({
                "role": "user",
                "content": f"Function {function_name} returned: {json.dumps(function_result)}"
            })
            return self._call_gemini_with_functions(current_messages, functions, max_iterations=3)

        else:
            # Groq and OpenRouter use OpenAI tools format
            # Need to first add the assistant message with tool calls, then the tool response
            # Find the last function call from messages
            tool_call_id = tool_use_id or "default"

            # Add assistant message with tool call (if not already present)
            # This is needed for proper OpenAI API format
            last_msg = current_messages[-1] if current_messages else {}
            if last_msg.get("role") != "assistant":
                # Need to reconstruct the assistant's tool call message
                current_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": json.dumps(function_result)  # This should be the function args, not result
                        }
                    }]
                })

            # Now add tool response
            current_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(function_result)
            })

            if self.groq_key:
                return self._call_groq_with_functions(current_messages, functions, max_iterations=3)
            elif self.openrouter_key:
                return self._call_openrouter_with_functions(current_messages, functions, max_iterations=3)
            else:
                raise RuntimeError("No provider available for continuation")

    def _convert_to_gemini_tools(self, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI function format to Gemini tools format."""
        tools = []

        for func in functions:
            tool = {
                "functionDeclarations": [{
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": func["parameters"]
                }]
            }
            tools.append(tool)

        return tools
