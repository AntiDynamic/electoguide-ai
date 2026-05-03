import asyncio
import os
from google import genai
from google.genai import types

async def main():
    client = genai.Client()
    config = types.GenerateContentConfig(
        temperature=0.7,
        system_instruction="You are a helpful assistant.",
    )
    contents = [
        {"role": "user", "parts": [{"text": "Hello, how are you?"}]}
    ]
    response = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config=config
    )
    print("Response:", response.text)

if __name__ == "__main__":
    asyncio.run(main())
