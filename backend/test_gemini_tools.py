from app.ai_service import generate_ai_response_with_tools

messages = [
    {
        "role": "user",
        "parts": [
            {
                "text": "Read the latest security alert email from Google and summarize it for me."
            }
        ]
    }
]

response = generate_ai_response_with_tools(messages)

print("\nGemini Final Response:")
print(response)


