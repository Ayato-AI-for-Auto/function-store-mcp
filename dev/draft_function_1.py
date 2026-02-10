
import os
import google.genai as genai
from typing import List, Dict

def summarize_text_gemini(text: str) -> str:
    """
    Summarizes a long text using Google's Gemini API.
    
    This function uses the 'gemini-2.5-flash' model to generate a concise summary 
    of the input text. It handles API key retrieval from the environment variable 
    'GOOGLE_API_KEY'.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Error: GOOGLE_API_KEY not found in environment."
    
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Summarize the following text concisely:\\n\\n{text}"
        )
        return response.text.strip()
    except Exception as e:
        return f"Error during summarization: {str(e)}"

# Test Cases
test_cases = [
    {
        "input": {"text": "Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation. Python is dynamically typed and garbage-collected. It supports multiple programming paradigms, including structured, object-oriented and functional programming."},
        "expected_output_type": "str"
    }
]

# Metadata
dependencies = ["google-genai"]
tags = ["text", "summary", "ai", "gemini"]
description = "Summarizes text using Gemini 2.5 Flash."
description_en = "Summarizes long text into a concise version using Google Gemini 2.5 Flash API."
description_jp = "Google Gemini 2.5 Flash APIを使用して、長いテキストを要約します。"
