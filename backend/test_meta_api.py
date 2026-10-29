import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("META_API_KEY")
base_url = os.getenv("META_API_BASE_URL", "https://api.meta.ai/v1")

print(f"Initializing Meta Model API client with base URL: {base_url}")
client = OpenAI(api_key=api_key, base_url=base_url)

try:
    response = client.chat.completions.create(
        model="muse-spark-1.3",
        messages=[
            {
                "role": "system",
                "content": "You are MetaECU Copilot, an expert automotive calibration AI agent.",
            },
            {
                "role": "user",
                "content": "Hello Muse Spark! Confirm your readiness for the Meta Global AI Developer Hackathon.",
            },
        ],
        max_tokens=1000,
    )

    msg = response.choices[0].message
    content = (
        msg.get("content")
        if isinstance(msg, dict)
        else getattr(msg, "content", str(msg))
    )

    print("\n--- Extracted Content ---")
    print(content)
    print("-------------------------")
    print("SUCCESS: Meta Model API connection verified successfully!")
except Exception as e:
    print(f"\nERROR connecting to Meta Model API: {e}")
