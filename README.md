# Mental Health Assessment Chatbot

A RAG-based conversational AI system that provides mental health support and conducts assessments with audio responses.

## Architecture Overview

The system follows this flow:
1. **RAG Chatbot**: Conversational AI using pre-built knowledge base
2. **Breakdown Trigger**: After 5-6 chats, suggests mental health assessment  
3. **Audio Assessment**: 7-question assessment with audio responses
4. **Comprehensive Report**: AI-generated report combining chat history and assessment

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Create `.env` file with your Groq API key:
```bash
GROQ_API_KEY=your_actual_groq_api_key_here
```

### 3. Prepare Vector Store
Ensure you have a pre-built FAISS vector store named `mental_health_vectorstore` in the project directory. This should contain embeddings of mental health documents.

### 4. Run the Application
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Chat Endpoint
**POST** `/chat`
```json
{
  "user_id": "user123",
  "message": "I've been feeling anxious lately"
}
```

### Get Assessment Questions
**GET** `/get_questions/{user_id}`

### Submit Audio Answer
**POST** `/submit_answer`
- Form data with `user_id`, `question_id`, and `audio_file`

### Generate Report
**POST** `/generate_report`
```json
{
  "user_id": "user123"
}
```

### Session Management
- **GET** `/session_status/{user_id}` - Get current session status
- **DELETE** `/clear_session/{user_id}` - Clear user session

## Usage Flow

1. **Start Chatting**: Use `/chat` endpoint for conversation
2. **Assessment Trigger**: After 5-6 messages, system suggests assessment
3. **Get Questions**: Retrieve assessment questions via `/get_questions`
4. **Submit Answers**: Upload audio responses using `/submit_answer`
5. **Generate Report**: Get comprehensive report via `/generate_report`

## Technical Stack

- **Framework**: FastAPI for REST API
- **LLM**: Groq Llama-3.3-70b-versatile
- **Embeddings**: HuggingFace sentence-transformers/all-mpnet-base-v2
- **Vector Store**: FAISS for similarity search
- **Audio Processing**: Groq Whisper-large-v3
- **Session Management**: In-memory storage (suitable for prototype)

## File Structure
```
project/
├── main.py                          # Main API application
├── questionnaire.json               # Assessment questions
├── .env                            # Environment variables
├── requirements.txt                # Dependencies
├── mental_health_vectorstore/      # Pre-built FAISS index
└── README.md                       # This file
```

## Key Features

- **Contextual Conversations**: RAG-based responses using mental health knowledge
- **Smart Triggers**: Automatic assessment suggestion after meaningful interaction
- **Audio Processing**: Real-time speech-to-text for assessment responses
- **Comprehensive Reports**: AI-generated insights combining all interaction data
- **Session Management**: Maintains conversation context per user
- **RESTful API**: Clean, documented endpoints for easy integration

## Notes

- This is a prototype version with in-memory session storage
- Audio files are processed temporarily and cleaned up automatically
- The system maintains conversation context for personalized interactions
- Reports are generated using structured prompts for consistent formatting