from openai import OpenAI

API_KEY = "6a17e2a5-b706-03cb-1a32-94b4a1df67da"
API_SERVER = "http://localhost:7777/v1"

client = OpenAI(
    api_key=API_KEY,
    base_url=API_SERVER
)


response = client.responses.create(
    model="gpt-4.1",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)
