"""
LLM Factory Module

Centralized factory for initializing LLM instances used by the agent,
separating fast interface models from reasoning models.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from settings import (
    INTERFACE_GEMINI_MODEL,
    REASONING_GEMINI_MODEL, 
    GEMINI_API_KEY 
)

def get_interface_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    """Fast, cheap model — used for chitchat detection and final answer formatting."""
    return ChatGoogleGenerativeAI(
        model=INTERFACE_GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=temperature,
    )
    
def get_reasoning_llm(temperature: float = 0) -> ChatGoogleGenerativeAI:
    """Capable model — drives the ReAct loop and generates Cypher queries."""
    return ChatGoogleGenerativeAI(
        model=REASONING_GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        temperature=temperature,
    )