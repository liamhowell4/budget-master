from openai import OpenAI, AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Endpoints:
    """OpenAI API client wrapper for standard OpenAI endpoints."""

    def __init__(self):
        api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        # Standard OpenAI API Client
        self.openai_client = OpenAI(api_key=api_key)

        # Standard OpenAI API Async Client
        self.openai_async_client = AsyncOpenAI(api_key=api_key)
