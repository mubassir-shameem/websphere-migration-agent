
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("ANTHROPIC_API_KEY")
print(f"Key loaded: {key[:10]}...")

try:
    client = anthropic.Anthropic(api_key=key)
    print("Attempting call with model: claude-sonnet-4-5")
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=10,
        messages=[
            {"role": "user", "content": "Hello, world"}
        ]
    )
    print("Success!")
    print(message.content)
except Exception as e:
    print(f"Error with claude-sonnet-4-5: {e}")

print("\nAttempting call with model: claude-3-5-sonnet-20240620")
try:
    client = anthropic.Anthropic(api_key=key)
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=10,
        messages=[
            {"role": "user", "content": "Hello, world"}
        ]
    )
    print("Success with 3.5!")
    print(message.content)
except Exception as e:
    print(f"Error with claude-3-5-sonnet-20240620: {e}")
