from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import re
import os
import uuid
import base64
import io
from curl_cffi import requests as curl_requests
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Genai client
api_key = os.environ.get("GOOGLE_CLOUD_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_CLOUD_API_KEY environment variable is not set. Please set it before starting the app.")

client = genai.Client(
    vertexai=True,
    api_key=api_key
)

ASPECT_RATIOS = {
    "Instagram Post (1:1)": "1:1",
    "Instagram Story (9:16)": "9:16",
    "Instagram Portrait (4:5)": "3:4",
    "Facebook Post (1:1)": "1:1",
    "Facebook Cover (16:9)": "16:9",
    "Facebook Story (9:16)": "9:16",
    "X Post (1:1)": "1:1",
    "X In-Stream (16:9)": "16:9",
    "YouTube Thumbnail (16:9)": "16:9",
    "YouTube Community Post (1:1)": "1:1",
    "WhatsApp Status (9:16)": "9:16",
    "WhatsApp Profile (1:1)": "1:1"
}

def get_amazon_images(url):
    impersonate_targets = ["chrome116", "safari15_5", "chrome110"]

    for target in impersonate_targets:
        try:
            print(f"Trying to fetch Amazon with impersonate={target}")
            # We use a session with curl_cffi to impersonate Browser's TLS fingerprint perfectly
            response = curl_requests.get(url, impersonate=target, timeout=15)
            
            # If the response length is super small, it's a captcha block
            if response.status_code == 503 or len(response.content) < 10000:
                print(f"Blocked or Captcha encountered (status {response.status_code}, len {len(response.content)}) mimicking {target}. Retrying...")
                continue
                
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Scrape Title
            title_tag = soup.find(id='productTitle')
            product_title = title_tag.get_text(strip=True) if title_tag else "Unknown Product"

            # 2. Scrape Description / Bullets
            product_desc = ""
            bullets = soup.select('#feature-bullets li span.a-list-item')
            if bullets:
                product_desc = " ".join([b.get_text(strip=True) for b in bullets[:4]])
            else:
                desc_tag = soup.find(id='productDescription')
                if desc_tag:
                    product_desc = desc_tag.get_text(strip=True)
            
            if len(product_desc) > 500:
                product_desc = product_desc[:500] + "..."
            
            script_content = None
            for script in soup.find_all('script'):
                if script.string and 'colorImages' in script.string:
                    script_content = script.string
                    break
                    
            image_urls = []
            if script_content:
                urls = re.findall(r'"hiRes":"(https://m\.media-amazon\.com/images/I/[^"\\\\]+\.jpg)"', script_content)
                if not urls:
                    urls = re.findall(r'"large":"(https://m\.media-amazon\.com/images/I/[^"\\\\]+\.jpg)"', script_content)
                image_urls = list(set(urls))
                
            if not image_urls:
                main_image = soup.find('img', id='landingImage')
                if main_image and main_image.get('data-old-hires'):
                    image_urls.append(main_image.get('data-old-hires'))
                elif main_image and main_image.get('src'):
                    image_urls.append(main_image.get('src'))

            if not image_urls:
                # If we successfully loaded a page but found zero images, it might be heavily loaded via JS or we got a soft block. Try next target.
                print(f"No images found with {target}, retrying...")
                continue

            saved_images = []
            for i, img_url in enumerate(image_urls):
                if i >= 10: 
                    break
                img_data = curl_requests.get(img_url, impersonate=target).content
                filename = f"amazon_img_{uuid.uuid4().hex[:8]}.jpg"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)
                saved_images.append(filepath.replace('\\', '/'))
            return saved_images, product_title, product_desc

        except Exception as e:
            print(f"Error scraping with target '{target}': {e}")
            continue
            
    # If all agents fail
    return [], "Unknown Product", ""

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
        
    if 'amazon' not in url.lower():
        return jsonify({'error': 'Please provide a valid Amazon link'}), 400
        
    images, title, desc = get_amazon_images(url)
    
    if not images:
        return jsonify({'error': 'Could not extract images. Amazon might be blocking the request.'}), 400
        
    return jsonify({
        'images': images,
        'title': title,
        'description': desc
    })

@app.route('/enhance_prompt', methods=['POST'])
def enhance_prompt():
    data = request.get_json()
    short_idea = data.get('idea', '')
    title = data.get('title', '')
    desc = data.get('description', '')
    
    if not short_idea:
        return jsonify({'error': 'No idea provided'}), 400
        
    try:
        system_instructions = """You are an expert AI prompt engineer. Your job is to transform the user's short idea into a highly detailed master prompt for an image generator. You MUST use the following exact stylistic template, replacing the bracketed section with the user's idea:

"High-end commercial product photography set against a vibrant, dynamic background that perfectly matches and complements the colors of the uploaded product. The lighting strategy is dramatic studio lighting with sharp rim-lighting to perfectly highlight the product's contours and textures. NO PEOPLE or human subjects should be in the image; the focus is entirely on the product itself. [INSERT THE USER'S SPECIFIC CREATIVE VISION FOR THE PRODUCT ENVIRONMENT AND COMPOSITION HERE based on their idea]. The product is vibrant, highly detailed, and glossy, standing out powerfully against the environment. Large, bold, industrial sans-serif text appears dynamically integrated at the top in a color matching the product."

Do NOT include any conversational text, intro, or outro. ONLY return the final assembled paragraph."""

        context_prompt = f"Product Title (for reference): {title}\nProduct Details (for reference): {desc}\n\nUser idea: {short_idea}\n\nGenerate the master prompt using the template, tailoring the environment and composition to fit this specific product naturally."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=context_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instructions,
                temperature=0.7,
            )
        )
        return jsonify({'prompt': response.text.strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate_caption', methods=['POST'])
def generate_caption():
    data = request.get_json()
    title = data.get('title', '')
    desc = data.get('description', '')
    idea = data.get('idea', '')
    
    prompt = f"""You are an expert social media manager.
Write a highly engaging social media caption for this product.
Product Title: {title}
Product Details: {desc}
User Request: {idea}

Format strictly like this:
[Catchy Headline]
[Short Engaging Body]
[3-5 relevant hashtags]
Keep it punchy, use emojis naturally, and make it ready to post!"""

    try:
        client = genai.Client(
            vertexai=True,
            api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return jsonify({'caption': response.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    image_paths = data.get('image_paths', [])
    gen_format = data.get('format', 'Instagram Post (1:1)')
    prompt_text = data.get('prompt', '')
    aspect_from_client = data.get('aspect_ratio')
    title = data.get('title', '')
    desc = data.get('description', '')

    if not image_paths or not isinstance(image_paths, list):
        return jsonify({'error': 'No images selected'}), 400

    contents = []

    # Process all image paths
    for p in image_paths:
        if os.path.exists(p):
            contents.append(Image.open(p))
            
    if not contents:
        return jsonify({'error': 'No valid images found to process.'}), 400

    # Build prompt
    aspect = aspect_from_client if aspect_from_client else ASPECT_RATIOS.get(gen_format, "1:1")
    
    reference_block = ""
    if title:
        reference_block = f"[Context Only: The uploaded product is '{title}'. Details: {desc}. Do NOT use this text in the image, just use it to understand what the object is].\n\n"
        
    full_prompt = f"{reference_block}Create a professional {gen_format}. {prompt_text}"
    contents.append(full_prompt)

    try:
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
                aspect_ratio=aspect,
            ),
        )

        # The user's code had a generate_content_stream, but image generation is just generate_content or generate_images.
        # But wait, gemini-3-pro-image-preview generates images, which does not stream.
        # So we just use generate_content
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=generate_content_config,
        )

        # Extract generated image from response
        generated_image_data = None
        response_text = ""
        
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                generated_image_data = part.inline_data.data
            elif part.text is not None:
                response_text += part.text

        if generated_image_data:
            # Save the generated image
            filename = f"gen_{uuid.uuid4().hex[:8]}.png"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(generated_image_data)
            
            # Return as base64 for immediate display + file path for download
            b64 = base64.b64encode(generated_image_data).decode('utf-8')
            return jsonify({
                'image_base64': b64,
                'image_path': filepath.replace('\\', '/'),
                'text': response_text,
            })
        else:
            return jsonify({'error': 'No image was generated. Try a different prompt.', 'text': response_text}), 400

    except Exception as e:
        print(f"Generation error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)