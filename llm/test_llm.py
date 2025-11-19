from openai import OpenAI
# Set OpenAI's API key and API base to use vLLM's API server.
openai_api_key = "sk-smXfLoe7jIs72ykN7fD157E58e194eEb9aDaCd359c05F5Dc"
openai_api_base = "http://10.249.238.110:8009/v1"

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

chat_response = client.chat.completions.create(
    model="qwen3-235b-a22b",
    messages=[
        {"role": "user", "content": "9.9和9.11哪个大？/no_think"},
    ],
    temperature=0.7,
    top_p=0.8,
    presence_penalty=1.5,
    extra_body={
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False}
    },
)
print("Chat response:", chat_response)