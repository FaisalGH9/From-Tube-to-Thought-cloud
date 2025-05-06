# From-Tube-To-Thought

<p align="center">
  <img src="logo.png" alt="From-Tube-To-Thought Logo" width="280"/>
</p>

<p align="center">
  <strong>Transform YouTube videos into interactive knowledge bases</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#repository-structure">Repository Structure</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#deployment">Deployment</a> •
  <a href="#license">License</a>
</p>

## Overview

From-Tube-To-Thought is a comprehensive AI-powered system that transforms YouTube videos into searchable, queryable knowledge bases. The application downloads, transcribes, and indexes video content, allowing users to ask questions and receive contextually relevant answers without watching the entire video.

Leveraging OpenAI's transcription and embedding models alongside advanced retrieval techniques, the system provides accurate responses based solely on what was actually spoken in the video.

## Features

- **YouTube Video Processing**: Download and transcribe videos with language detection
- **Interactive Querying**: Ask natural language questions about video content
- **Multi-Language Support**: Processes and responds in English, Arabic, Spanish, Italian, and Swedish
- **Smart Summarization**: Generate concise summaries at various detail levels
- **Advanced Retrieval**: Hybrid vector and keyword search for optimal content matching
- **Intelligent Caching**: Multi-level caching system for improved performance
- **Responsive UI**: Streamlit-based interface with real-time processing feedback
- **Configurable Processing**: Options for processing duration, quality, and performance

## Architecture

The system follows a modular architecture with six primary components:

1. **Processing Engine** (`core/engine.py`): Orchestrates the overall workflow
2. **YouTube Service** (`services/youtube.py`): Handles video access and audio extraction
3. **Transcription Service** (`transcription/service.py`): Converts audio to text with language detection
4. **Vector Store** (`retrieval/vector_store.py`): Indexes and retrieves relevant content
5. **LLM Provider** (`llm/provider.py`): Generates natural language responses
6. **Cache Manager** (`cache/manager.py`): Optimizes performance with multi-level caching

### Data Flow Pipeline

```
YouTube URL → Audio Download → Transcription → Chunking → Vector Indexing → Query Processing → Response Generation
```

1. User submits a YouTube URL
2. System downloads audio using PyTubeFix with proxy support
3. Audio is transcribed using OpenAI's Whisper model
4. Transcript is chunked using semantic-aware adaptive splitting
5. Content is indexed using OpenAI embeddings and BM25
6. User queries are processed with hybrid semantic/keyword search
7. Contextually relevant responses are generated via OpenAI's language models

## Installation

### Prerequisites

- Python 3.10+
- FFmpeg
- OpenAI API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/from-tube-to-thought.git
   cd from-tube-to-thought
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   PROXY_URL=your_proxy_url  # Optional
   ```

## Usage

Run the Streamlit application:

```bash
streamlit run main.py
```

The web interface will be available at `http://localhost:8501`.

1. Enter a YouTube URL in the input field
2. Configure processing options if needed
3. Click "Process" to start video analysis
4. Once processing completes, you can:
   - Ask questions about the video content in the Chat tab
   - Generate summaries of different lengths in the Summary tab

## Repository Structure

```
from-tube-to-thought/
├── cache/
│   └── manager.py         # Multi-level caching system
├── config/
│   └── settings.py        # Configuration settings
├── core/
│   └── engine.py          # Main processing orchestration
├── llm/
│   └── provider.py        # Language model interface
├── retrieval/
│   ├── chunking.py        # Text chunking strategies
│   └── vector_store.py    # Vector and BM25 search
├── services/
│   └── youtube.py         # YouTube downloader
├── transcription/
│   └── service.py         # Audio transcription
├── main.py                # Streamlit UI
├── Dockerfile             # Container definition
├── requirements.txt       # Dependencies
├── logo.png               # Application logo
└── README.md              # This file
```

## Configuration

Key settings can be adjusted in `config/settings.py`:

- **LLM Models**: Configure model selection for different tasks
- **Chunking Parameters**: Adjust chunk size and overlap
- **Caching Settings**: Set TTL (time-to-live) for cache entries
- **Performance Options**: Configure concurrent processing limits
- **Audio Quality**: Set bitrate for downloaded audio

## Deployment

### Local Development

Run the application locally with:

```bash
streamlit run main.py
```

### Docker Deployment

Build and run using Docker:

```bash
docker build -t from-tube-to-thought .
docker run -p 8080:8080 -e PORT=8080 -e OPENAI_API_KEY=your_key from-tube-to-thought
```

### Google Cloud Run

The included Dockerfile is configured for deployment on Google Cloud Run:

```bash
gcloud builds submit --tag gcr.io/your-project/from-tube-to-thought
gcloud run deploy --image gcr.io/your-project/from-tube-to-thought --platform managed
```

Environment variables to set in Cloud Run:
- `OPENAI_API_KEY`: Your OpenAI API key
- `CLOUD_RUN`: Set to "true"


## License

[MIT License](LICENSE)

## License

[MIT License](LICENSE)

## Acknowledgements

- [OpenAI](https://openai.com/) for providing the AI models
- [PyTubeFix](https://github.com/JuanBindez/pytubefix) for YouTube integration
- [LangChain](https://langchain.com/) for vector store components
- [Streamlit](https://streamlit.io/) for the user interface framework

---

Created with 💙 by [FaisalGH9]
