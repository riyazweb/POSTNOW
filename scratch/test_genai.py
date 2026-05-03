import os
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(
    vertexai=True,
    api_key=os.environ.get("GOOGLE_CLOUD_API_KEY")
)

model = "gemini-2.5-flash-image"
source_image = Image.new('RGB', (100, 100), color = 'red')

contents = [source_image, "Create a professional post"]

generate_content_config = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    max_output_tokens=32768,
    response_modalities=["IMAGE"],
    safety_settings=[
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    ],
    image_config=types.ImageConfig(
        aspect_ratio="1:1",
    ),
)

try:
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    print("Success")
except Exception as e:
    print("Error:", repr(e))
