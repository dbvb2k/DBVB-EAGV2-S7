# Web Indexer Backend

A Flask-based backend service for the Chrome extension that provides web page indexing, semantic search, and chatbot capabilities.

## Features

- Web page content indexing using FAISS
- Semantic search using Nomic embeddings
- Chatbot integration with Google's Gemini
- RESTful API endpoints
- CORS support for Chrome extension

## Prerequisites

- Python 3.11 or 3.12 (recommended: 3.11)
- pip or uv package manager

## Installation

### Option 1: Using uv (Recommended)

```bash
# Navigate to backend directory
cd backend

# Install dependencies using uv
uv pip install -r requirements.txt
```

### Option 2: Using pip

```bash
# Navigate to backend directory
cd backend

# Create a virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the backend directory with the following content:

```env
NOMIC_API_KEY=your-nomic-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=dev-key-please-change-in-production
```

2. Get your API keys:
   - **Nomic API Key** (Required): https://atlas.nomic.ai/
   - **Gemini API Key** (Optional for chat): https://makersuite.google.com/app/apikey

## Running the Server

### Development Mode

```bash
python wsgi.py
```

Or using Flask CLI:

```bash
flask run
```

The server will start on `http://localhost:5000`

### Production Mode

```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

## API Endpoints

### Health Check
- **GET** `/api/health`
- Returns: Server status and index size

### Index Page
- **POST** `/api/index`
- Body: `{ "url": "https://example.com", "title": "Page Title", "content": "page content" }`
- Returns: Document ID

### Search
- **POST** `/api/search`
- Body: `{ "query": "search query", "limit": 5 }`
- Returns: Array of search results

### Chat
- **POST** `/api/chat`
- Body: `{ "query": "chat query" }`
- Returns: Chat response

### Check if Indexed
- **POST** `/api/check-indexed`
- Body: `{ "url": "https://example.com" }`
- Returns: Whether URL is indexed

### Get Stats
- **GET** `/api/stats`
- Returns: Index statistics

### Regenerate Test Data
- **POST** `/api/regenerate-test-data`
- Adds sample pages to the index for testing

### Download Index
- **GET** `/api/download-index`
- Downloads the FAISS index and metadata as a ZIP file

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| flask | 3.0.3 | Web framework |
| flask-cors | 4.0.1 | CORS support |
| python-dotenv | 1.0.1 | Environment variables |
| faiss-cpu | 1.7.4 | Vector similarity search |
| numpy | >=1.24.0,<1.27.0 | Numerical operations |
| nomic | 3.6.0 | Embedding generation |
| google-generativeai | 0.8.3 | Gemini AI integration |
| gunicorn | 23.0.0 | Production WSGI server |

## Troubleshooting

### Import Errors

If you encounter DLL load errors with FAISS:

1. Ensure you're using Python 3.11 or 3.12
2. Reinstall faiss-cpu: `pip uninstall faiss-cpu && pip install faiss-cpu==1.7.4`
3. Verify numpy is compatible: `pip install "numpy>=1.24.0,<1.27.0"`

### API Key Errors

If you see "NOMIC_API_KEY is not configured":

1. Verify the `.env` file exists in the `backend` directory
2. Check that the file contains `NOMIC_API_KEY=your-actual-key`
3. Restart the server after adding the key

### Port Already in Use

If port 5000 is already in use:

```bash
# Change the port in wsgi.py
app.run(host='0.0.0.0', port=5001, debug=True)
```

## Development

- The backend uses Flask's application factory pattern
- Services are modular and can be easily extended
- FAISS index is persisted to disk at `backend/data/`
- Logs are configured to show INFO level messages

## License

This project is part of the Chrome Extension Web Indexer system.
