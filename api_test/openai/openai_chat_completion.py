from openai import OpenAI

API_KEY = "6a17e2a5-b706-03cb-1a32-94b4a1df67da"
API_SERVER = "http://localhost:7777/v1"

client = OpenAI(
    api_key=API_KEY,
    base_url=API_SERVER
)


completion = client.chat.completions.create(
  model="gpt-4.1",
  messages=[
    {"role": "developer", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  stream=True
)

for chunk in completion:
    print(chunk)
    
#print(completion.id)

#print(completion.choices[0].message)