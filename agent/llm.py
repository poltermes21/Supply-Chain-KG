"""
Central LLM factory
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from settings import (
    INTERFACE_GEMINI_MODEL,
    REASONING_GEMINI_MODEL, 
    GEMINI_API_KEY 
)

def get_interface_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=INTERFACE_GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=temperature,
    )
    
def get_reasoning_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=REASONING_GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=temperature,
    )