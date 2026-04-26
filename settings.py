"""
Settings Module

Loads environment variables for system configuration.
Provides centralized access to all configuration values.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

# =============================================================================
# DATA CONFIGURATION
# =============================================================================

DATA_DIR = os.getenv("DATA_DIRECTORY", "data")
DATA_FILENAME = os.getenv("RAW_DATA", "raw/global_supply_chain_v2.csv")

# =============================================================================
# NEO4J CONFIGURATION
# =============================================================================

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================

INTERFACE_GEMINI_MODEL = os.getenv("INTERFACE_GEMINI_MODEL", "gemini-2.0-flash")
REASONING_GEMINI_MODEL = os.getenv("REASONING_GEMINI_MODEL", "gemini-2.5-pro")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "password")

# =============================================================================
# HELPER FUNCTION
# =============================================================================

def print_config():
    """Print current configuration (hides password)."""
    print("="*60)
    print("CURRENT CONFIGURATION")
    print("="*60)
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"DATA_FILENAME: {DATA_FILENAME}")
    print(f"NEO4J_URI: {NEO4J_URI}")
    print(f"NEO4J_USER: {NEO4J_USER}")
    print(f"NEO4J_PASSWORD: {'*' * len(NEO4J_PASSWORD)}")
    print(f"INTERFACE_GEMINI_MODEL: {INTERFACE_GEMINI_MODEL}")
    print(f"REASONING_GEMINI_MODEL: {REASONING_GEMINI_MODEL}")
    print(f"GEMINI_API_KEY: {'*' * len(GEMINI_API_KEY)}")
    print("="*60)


if __name__ == "__main__":
    print_config()
