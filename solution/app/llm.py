import os 
import httpx
from typing import Any

class OllamaClient:
    def __init__(self) -> None:
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("MODEL_NAME", "llama3.2:3b")
        self.client = httpx.AsyncClient(base_url=self.host, timeout=60.0) #wrapper

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.2, format: str | None = None) -> str:
        """
        Sends a conversation history to the Ollama local API and returns the response string.
        """
        url = "/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if format:
            payload["format"] = format
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return str(data["message"]["content"])
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.host}. Is Ollama running? Run `ollama serve` or start the desktop app."
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama API returned an error status: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error communicating with Ollama: {str(e)}")

    async def close(self) -> None:
        await self.client.aclose()