from google import genai
from google.genai import types
import os

def generate():
    # If using gs:// URIs, Vertex AI must be used.
    # Vertex AI uses Default Application Credentials (ADC) rather than a direct API key.
    # Ensure you have run `gcloud auth application-default login` or set GOOGLE_APPLICATION_CREDENTIALS.
    # If you intend to use Google AI Studio with an API key, you cannot use gs:// URIs.
    # Assuming Vertex AI based on gs:// usage:
    client = genai.Client(
        vertexai=True,
        location="us-central1"
    )

    image1 = types.Part.from_uri(
        file_uri="gs://cloud-samples-data/generative-ai/image/woman.jpg",
        mime_type="image/jpeg",
    )
    image2 = types.Part.from_uri(
        file_uri="gs://cloud-samples-data/generative-ai/image/suitcase.png",
        mime_type="image/png",
    )
    image3 = types.Part.from_uri(
        file_uri="gs://cloud-samples-data/generative-ai/image/armchair.png",
        mime_type="image/png",
    )
    image4 = types.Part.from_uri(
        file_uri="gs://cloud-samples-data/generative-ai/image/man-in-field.png",
        mime_type="image/png",
    )
    image5 = types.Part.from_uri(
        file_uri="gs://cloud-samples-data/generative-ai/image/shoes.jpg",
        mime_type="image/jpeg",
    )
    image6 = types.Part.from_uri(
        file_uri="gs://cloud-samples-data/generative-ai/image/living-room.png",
        mime_type="image/png",
    )
    text1 = types.Part.from_text(text="""Generate an image of a woman sitting in a living room with a man. The man is wearing the brown sneakers. The woman is wearing a red version of the sneakers. The woman is sitting in a white armchair with a blue suitcase next to her.""")

    model = "gemini-3.1-flash-image-preview"
    contents = [
        types.Content(
            role="user",
            parts=[
                image1,
                image2,
                image3,
                image4,
                image5,
                image6,
                text1
            ]
        )
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=32768,
        response_modalities=["TEXT", "IMAGE"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ],
        image_config=types.ImageConfig(
            aspect_ratio="auto",
            image_size="1K",
            output_mime_type="image/png",
        ),
        thinking_config=types.ThinkingConfig(
            thinking_level="HIGH",
        ),
    )

    try:
        # Stream response chunks
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            print(chunk.text, end="")
    except Exception as e:
        print(f"Error during generation: {e}")

if __name__ == "__main__":
    generate()
