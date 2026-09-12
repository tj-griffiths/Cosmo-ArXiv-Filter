# Hosts API client for Cosmo pipeline

import os
import time
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"
API_KEY_FILE = "groq_api_key.txt"
MODEL_FILE = "groq_model.txt"

DEFAULT_SYSTEM_PROMPT = (
    "You are a physicist explaining research papers to fellow physics "
    "graduate students (master's level) who are not specialists in this "
    "particular subfield. Assume a solid general physics background "
    "(quantum mechanics, statistical mechanics, electromagnetism, etc.) "
    "but don't assume familiarity with this subfield's specific jargon, "
    "notation, or named techniques — briefly explain those when they "
    "come up, rather than either leaving them undefined or over-"
    "simplifying to a general-audience level."
)

def _get_api_key() -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        return api_key
    
    key_file_path = os.path.join(os.path.dirname(__file__), API_KEY_FILE)
    if os.path.exists(key_file_path):
        with open(key_file_path) as f:
            api_key = f.read().strip()
        if api_key:
            return api_key
    
    raise RuntimeError(
        f"No Groq API key found. Get a free key at "
        f"https://console.groq.com/keys, then either set it as an "
        f'environment variable (export GROQ_API_KEY="your-key-here") '
        f"or save it as plain text in a file named {API_KEY_FILE} in "
        f"this same folder (make sure that filename is in .gitignore)."
    )

def _get_model()-> str:
    model = os.environ.get("GROQ_MODEL")
    if model:
        return model
    
    model_file_path = os.path.join(os.path.dirname(__file__), MODEL_FILE)
    if os.path.exists(model_file_path):
        with open(model_file_path) as f:
            model = f.read().strip()
        if model:
            return model
    
    return DEFAULT_MODEL

def generate(
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 600,
) -> str:
    """ 
    Sends a single-turn prompt to the hosted LLM and returns its response text.
    """

    try:
        api_key = _get_api_key()
    except RuntimeError as e:
        return f"Error: {e}"
    
    model = _get_model()
    
    try:
        response = requests.post(
            GROQ_API_URL,
            headers = {"Authorization": f"Bearer {api_key}"},
    
            json = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "reasoning_effort": "low"
            },
            timeout = 30,
        )
    except requests.exceptions.ConnectionError:
        return "[Could not reach Groq's API - check your internet connection.]"
    except requests.exceptions.Timeout:
        return "[Request to Groq's API timed out - try again later.]"
    if response.status_code == 401:
        return "[Groq rejected the API key (401) - check that GROQ_API_KEY is set correctly.]"
    if response.status_code == 404:
        return (
            f"[Groq returned 404 for model '{model}' — it's likely been "
            f"deprecated. Check https://console.groq.com/docs/models for the "
            f"current list, then either edit GROQ_MODEL in api.py or set the "
            f"GROQ_MODEL environment variable to override it without editing "
            f"code.]"
        )
    if response.status_code == 429:
        return "[Hit Groq's free-tier limit (429) - wait a bit and try again.]"
    if response.status_code != 200:
        return f"[Groq returned HTTP {response.status_code}: {response.text[:200]!r}]"
    
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()
    if not content:
        return "[Groq returned an empty response - try again.]"
    return data["choices"][0]["message"]["content"].strip()
    