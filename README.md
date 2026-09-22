# POSTNOW / PIXI
 <img width="796" height="712" alt="image" src="https://github.com/user-attachments/assets/2eeeebc9-4c1c-4b3c-b187-054fc52cfbe0" />

An intelligent, containerized Flask app leveraging Generative AI for content creation.

## ?? Features
- **AI Content Generation**
- **Trend Analysis**
- **Clean Web Interface**
- **Docker Ready**

## ??? Tech Stack
- **Backend:** Python, Flask
- **Deployment:** Docker

## ?? Getting Started

### Local Setup
1. Create a virtual environment: `python -m venv .venv`
2. Activate: `.\.venv\Scripts\activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python app.py`

### Dockerized
``bash
docker build -t pixi .
docker run -p 5000:5000 pixi
``
