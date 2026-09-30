VYRA

VYRA is an AI-powered commercial and personal assistant designed to help professionals manage contacts, conversations, tasks, context, and AI-assisted responses.

V1 Features

- Professional user profile
- Contact management
- Conversation management
- Message history
- AI-assisted response suggestions
- Human validation before sending
- Tasks and reminders
- Conversation memory and context
- Dashboard and API
- Gemini AI integration

Architecture

app/
├── main.py
├── core/
├── models/
├── schemas/
├── api/
├── services/
└── ai/

AI

VYRA supports an AI gateway architecture so the AI provider can be changed without rewriting the application.

The Gemini API key is provided through an environment variable:

"GEMINI_API_KEY"

Never commit API keys or other secrets to GitHub.

Running the application

Install dependencies:

pip install -r requirements.txt

Start the API:

uvicorn app.main:app --host 0.0.0.0 --port 8000

Status

VYRA V1 is under active development.

Security

Secrets, environment files, local databases, caches, and temporary Python files are excluded from version control.