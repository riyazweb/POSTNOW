# POSTNOW / PIXI

<div align="center">

**AI-powered content creation, built for speed.**

Generate sharper ideas, analyze trends, and turn inspiration into publish-ready content from one clean, containerized Flask app.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-Web%20App-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## ✨ What is POSTNOW?

**POSTNOW**, also known as **PIXI**, is an intelligent content creation platform powered by Generative AI. It combines a simple web interface with trend-aware workflows to help you move from an idea to engaging content faster.

## 🚀 Features

- **AI content generation** — Create drafts, captions, hooks, and ideas with less effort.
- **Trend analysis** — Use emerging topics and audience interests to guide your content.
- **Clean web interface** — Focus on the work with a straightforward Flask-powered UI.
- **Container-ready deployment** — Run consistently across local environments and servers with Docker.
- **Simple developer workflow** — Get started quickly with a lightweight Python setup.

## 🧰 Tech stack

| Layer | Technology |
| --- | --- |
| Backend | Python + Flask |
| AI | Generative AI integrations |
| Deployment | Docker |
| Interface | Web-based UI |

## 📦 Getting started

### Prerequisites

Make sure you have the following installed:

- [Python 3.10+](https://www.python.org/downloads/)
- `pip`
- [Docker](https://docs.docker.com/get-docker/) — optional, for containerized deployment

### Run locally

1. **Clone the repository**

   ```bash
   git clone https://github.com/riyazweb/POSTNOW.git
   cd POSTNOW
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   ```

3. **Activate the environment**

   **Windows PowerShell**

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS / Linux**

   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Start the application**

   ```bash
   python app.py
   ```

6. Open [http://localhost:5000](http://localhost:5000) in your browser.

### Run with Docker

Build the image:

```bash
docker build -t postnow .
```

Start the container:

```bash
docker run --rm -p 5000:5000 postnow
```

Then visit [http://localhost:5000](http://localhost:5000).

## 🔐 Configuration

If the application requires API keys or other secrets, store them in environment variables or a local `.env` file. Never commit credentials to the repository.

Example:

```env
AI_API_KEY=your_api_key_here
```

> Use the exact variable names expected by the application configuration.

## 🗂️ Project structure

```text
POSTNOW/
├── app.py              # Flask application entry point
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container image configuration
├── templates/          # HTML templates
├── static/             # CSS, JavaScript, and assets
└── README.md           # Project documentation
```

> The structure may evolve as the project grows.

## 🤝 Contributing

Contributions are welcome. To contribute:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature`.
3. Make your changes and test them locally.
4. Commit your work: `git commit -m "Add your feature"`.
5. Push the branch and open a pull request.

## 📄 License

Add your project license here when one is selected.

---

<div align="center">

**Create less. Publish more.**

Built with Python, Flask, and a little AI magic.

</div>
