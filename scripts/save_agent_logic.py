
import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client

# 1. Context Compressor
code_compressor = r'''
import os
import json
from typing import List, Dict, Any, Optional

def compress_conversation_history(messages: List[Dict[str, str]], threshold: int = 15, keep_recent: int = 8, api_key: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Compresses conversation history using a sliding window and LLM summarization.
    
    Args:
        messages: List of message dicts {"role": str, "content": str}.
        threshold: Max messages before triggering compression.
        keep_recent: Number of recent messages to keep raw.
        api_key: Google API Key.
        
    Returns:
        New list of messages with older ones summarized.
    """
    import google.generativeai as genai
    
    if len(messages) <= threshold:
        return messages
        
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        print("Warning: No API Key for compression. Returning raw.")
        return messages

    # Slice
    to_summarize = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]
    
    # Preserve System Prompt (if first)
    system_prompt = None
    if to_summarize and to_summarize[0].get("role") == "system":
        system_prompt = to_summarize.pop(0)

    if not to_summarize:
        return messages

    # Format for LLM
    conversation_text = ""
    for msg in to_summarize:
        conversation_text += f"{msg.get('role', 'unknown')}: {msg.get('content', '')}\n"

    prompt = f"""
    Summarize the conversation below into a concise paragraph.
    Preserve key decisions, facts, and current status.
    
    CONVERSATION:
    {conversation_text}
    """
    
    # Generate Summary
    try:
        genai.configure(api_key=key)
        # Use a cheap/fast model for summarization
        model = genai.GenerativeModel('gemini-2.5-flash-lite') 
        response = model.generate_content(prompt)
        summary_text = response.text.strip()
        
        summary_message = {
            "role": "system", 
            "content": f"*** PREVIOUS CONVERSATION SUMMARY ***\n{summary_text}"
        }
        
        new_history = []
        if system_prompt: new_history.append(system_prompt)
        new_history.append(summary_message)
        new_history.extend(recent_messages)
        
        return new_history
        
    except Exception as e:
        print(f"Compression failed: {e}")
        return messages
'''

# 2. Circuit Breaker
code_circuit_breaker = r'''
import time
from typing import Dict, Any

# Global state for the function runtime
_CB_FAILURES = {}
_CB_COOLDOWNS = {}

def manage_circuit_breaker(identifier: str, action: str = "check", error_type: str = "generic") -> Dict[str, Any]:
    """
    Manages a simple Circuit Breaker pattern.
    
    Args:
        identifier: Service or Model ID.
        action: "check", "success", "failure".
        error_type: "generic" or "rate_limit" (for failure action).
        
    Returns:
        {"is_open": bool, "message": str}
    """
    global _CB_FAILURES, _CB_COOLDOWNS
    
    THRESHOLD = 3
    RESET_TIMEOUT = 300 # 5 min
    RATE_LIMIT_COOLDOWN = 60 # 1 min
    
    current_time = time.time()
    
    if action == "check":
        if identifier in _CB_COOLDOWNS:
            if current_time < _CB_COOLDOWNS[identifier]:
                remaining = int(_CB_COOLDOWNS[identifier] - current_time)
                return {"is_open": True, "message": f"Circuit Open. Cooling down for {remaining}s"}
            else:
                # Cleanup expired
                del _CB_COOLDOWNS[identifier]
                _CB_FAILURES[identifier] = 0
        return {"is_open": False, "message": "OK"}
        
    elif action == "success":
        if identifier in _CB_FAILURES: del _CB_FAILURES[identifier]
        if identifier in _CB_COOLDOWNS: del _CB_COOLDOWNS[identifier]
        return {"is_open": False, "message": "Reset"}
        
    elif action == "failure":
        if error_type == "rate_limit":
            _CB_COOLDOWNS[identifier] = current_time + RATE_LIMIT_COOLDOWN
            return {"is_open": True, "message": "Rate Limit detected. Cooldown set."}
            
        count = _CB_FAILURES.get(identifier, 0) + 1
        _CB_FAILURES[identifier] = count
        
        if count >= THRESHOLD:
            _CB_COOLDOWNS[identifier] = current_time + RESET_TIMEOUT
            return {"is_open": True, "message": f"Threshold reached ({count}). Circuit Broken."}
            
        return {"is_open": False, "message": f"Failure recorded ({count}/{THRESHOLD})"}
        
    return {"is_open": False, "message": "Unknown action"}
'''

async def save_agent_functions():
    url = "http://localhost:8001/sse"
    print(f"Connecting to {url}...")
    
    async with sse_client(url) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            # Save Compressor
            print("Saving compress_conversation_history...")
            await session.call_tool("save_function", arguments={
                "name": "compress_conversation_history",
                "code": code_compressor,
                "description": "Compresses long conversation history using Gemini summarization.",
                "tags": ["agent", "memory", "utility", "gemini"],
                "dependencies": ["google-generativeai"],
                "auto_generate_tests": False
            })
            
            # Save Circuit Breaker
            print("Saving manage_circuit_breaker...")
            await session.call_tool("save_function", arguments={
                "name": "manage_circuit_breaker",
                "code": code_circuit_breaker,
                "description": "Implements Circuit Breaker pattern for API reliability.",
                "tags": ["reliability", "utils", "pattern"],
                "dependencies": [],
                "auto_generate_tests": False
            })

            print("Agent functions saved!")

if __name__ == "__main__":
    asyncio.run(save_agent_functions())
