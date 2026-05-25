import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="hf-inference",
    api_key=os.environ["HUGGINGFACE_API_KEY"],
)

result = client.translation(
    "Меня зовут Вольфганг и я живу в Берлине",
    model="tencent/Hy-MT2-1.8B",
)