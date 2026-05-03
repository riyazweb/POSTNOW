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
import json
import time
import datetime
import holidays
import feedparser

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Genai client
api_key = os.environ.get("GOOGLE_CLOUD_API_KEY") or os.environ.get("GEMINI_API_KEY")

try:
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        # Try finding credentials from Vertex AI/Default ADC
        client = genai.Client(vertexai=True, location="us-central1")
except Exception as e:
    print(f"Warning: Failed to initialize genai.Client: {e}")
    client = None

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
                b64 = base64.b64encode(img_data).decode('utf-8')
                saved_images.append(f"data:image/jpeg;base64,{b64}")
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

TRENDS_CACHE_FILE = 'trends_cache.json'

@app.route('/api/trends', methods=['GET'])
def get_trends():
    current_time = time.time()
    
    # 1. Check local JSON cache
    if os.path.exists(TRENDS_CACHE_FILE):
        try:
            with open(TRENDS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            # 6 hours = 21600 seconds
            if cache and cache.get('data') and (current_time - cache.get('timestamp', 0) < 21600):
                return jsonify(cache['data'])
        except Exception as e:
            print(f"Cache read error: {e}")
            pass
            
    try:
        # 1. Fetch RSS using feedparser
        feed = feedparser.parse('https://trends.google.com/trending/rss?geo=IN')
        trends = []
        for entry in feed.entries[:10]:
            title = entry.title if hasattr(entry, 'title') else ""
            news_title = entry.ht_news_item_title if hasattr(entry, 'ht_news_item_title') else ""
            trends.append(f"{title} - {news_title}")
            
        # 2. Fetch Holidays
        in_holidays = holidays.IN(years=datetime.date.today().year)
        upcoming = []
        for dt, name in sorted(in_holidays.items()):
            if dt >= datetime.date.today():
                upcoming.append(f"{dt.strftime('%b %d')}: {name}")
            if len(upcoming) >= 5:
                break
                
        # 3. Ask Gemini for specific ideas based on trends/holidays
        current_day_name = datetime.date.today().strftime("%A")
        
        prompt = f"""You are an expert social media and visual marketing AI. 
Today is {current_day_name}.

Here is the FULL LIST of top trending topics in India right now:
{chr(10).join(trends)}

Here are the upcoming holidays:
{chr(10).join(upcoming)}

Generate a JSON array of creative social media post visual themes based STRICTLY on these specific trends, holidays, and the current day of the week.

CRITICAL RULES:
1. You MUST generate exactly ONE unique idea for EVERY SINGLE trend listed above. Do not skip any trends. If there are 10 trends, generate 10 ideas.
2. You MUST generate exactly 4 ideas based ONLY on the current day of the week ({current_day_name}) (e.g., if it's Sunday, "Summer Sunday", "Sunday Funday", "Lazy Sunday", etc).
3. Do NOT use generic categories like "Sports Fever". You MUST explicitly use the exact names of the trending people, teams, movies, or holidays.
If "Shubman Gill" is trending, the button_label MUST mention "Shubman Gill", and the hidden_prompt MUST explicitly describe a scene with "Shubman Gill's team colors, cricket jersey aesthetic, stadium".

These prompts will be used as background generators for e-commerce products.
Format the output EXACTLY as a JSON array of objects with:
"button_label": A short, catchy 2-4 word phrase explicitly naming the trend or day (e.g., "Shubman Gill Vibe 🏏", "Sunday Funday ☀️").
"hidden_prompt": A highly detailed visual background prompt setting a beautiful aesthetic scene explicitly mentioning the trend's colors/theme or the day's vibe, WITHOUT mentioning any specific e-commerce product (e.g., "Set in a vibrant cricket stadium using Shubman Gill's team colors (blue and gold)..." or "A bright, sunny Sunday morning aesthetic with soft light and coffee elements...").

Output ONLY the raw JSON array. No markdown, no intro."""

        client_inst = genai.Client(api_key=api_key) if api_key else genai.Client(vertexai=True, location="us-central1")
        response = client_inst.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        text = response.text.replace('```json', '').replace('```', '').strip()
        ideas = json.loads(text)
        
        data_to_return = {'success': True, 'ideas': ideas}
        
        # Save to local JSON storage
        try:
            with open(TRENDS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({'data': data_to_return, 'timestamp': current_time}, f)
        except Exception as e:
            print(f"Cache write error: {e}")
            
        return jsonify(data_to_return)
        
    except Exception as e:
        print(f"Error fetching trends: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        client_inst = genai.Client(api_key=api_key) if api_key else genai.Client(vertexai=True, location="us-central1")
        response = client_inst.models.generate_content(
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
        if p.startswith('data:image/'):
            head, b64_data = p.split(',', 1)
            img_data = base64.b64decode(b64_data)
            contents.append(Image.open(io.BytesIO(img_data)))
        elif os.path.exists(p):
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
            response_modalities=["TEXT", "IMAGE"],
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
            ],
            image_config=types.ImageConfig(
                aspect_ratio=aspect,
                image_size="1K",
                output_mime_type="image/png",
            ),
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH",
            ),
        )

        # The user's code had a generate_content_stream, but image generation is just generate_content or generate_images.
        # But wait, gemini-3-pro-image-preview generates images, which does not stream.
        # So we just use generate_content
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
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
            # Return as base64 without saving to disk
            b64 = base64.b64encode(generated_image_data).decode('utf-8')
            return jsonify({
                'image_base64': b64,
                'image_path': f"data:image/png;base64,{b64}",
                'text': response_text,
            })
        else:
            return jsonify({'error': 'No image was generated. Try a different prompt.', 'text': response_text}), 400

    except Exception as e:
        print(f"Generation error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
