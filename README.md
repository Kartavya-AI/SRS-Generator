# Conversational SRS Generator
A conversational AI-powered tool that helps generate Software Requirements Specifications (SRS) through natural language interactions. The system uses Google's Gemini AI to conduct intelligent Q&A sessions and automatically create professional SRS documents.

## 🌟 Features
- **Conversational Interface**: Natural language interaction for requirements gathering
- **Multi-Specialist Support**: Tailored questioning for different project types
- **Voice Input/Output**: Speech-to-text and text-to-speech capabilities
- **Multi-Language Support**: Voice input in English, Hindi, Tamil, and Malayalam
- **Dual Interface**: Both web-based Streamlit app and REST API
- **Document Export**: Generate PDF documents of the final SRS
- **Real-time Processing**: Dynamic question generation based on user responses

## 🏗️ Architecture

The project consists of three main components:
1. **Streamlit Web App** (`app.py`) - Interactive web interface
2. **FastAPI REST API** (`api.py`) - RESTful API for integration
3. **Core Logic** (`tool.py`) - AI-powered question generation and SRS creation

## 🔧 Prerequisites
- Python 3.11+
- Google Gemini API key
- Microphone access (for voice input)
- Internet connection (for speech recognition services)

## 📦 Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Kartavya-AI/SRS-Generator
   cd SRS-Generator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Additional requirements for Streamlit app**
   ```bash
   pip install streamlit fpdf gtts streamlit-mic-recorder
   ```

4. **Download DejaVu font** (for PDF generation)
   - Download `DejaVuSans.ttf` and place it in the project root directory

### Docker Deployment

1. **Build the Docker image**
   ```bash
   docker build -t srs-generator .
   ```

2. **Run the container**
   ```bash
   docker run -p 8080:8080 srs-generator
   ```

## 🚀 Usage

### Streamlit Web Application

1. **Start the Streamlit app**
   ```bash
   streamlit run app.py
   ```

2. **Access the application**
   - Open your browser to `http://localhost:8501`

3. **Using the interface**
   - Enter your Gemini API key in the sidebar
   - Select a specialist type (AI/ML, Android, iOS, etc.)
   - Provide initial requirements via text or voice
   - Answer the generated questions
   - Review and download the final SRS document

### REST API

1. **Start the FastAPI server**
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8080
   ```

2. **API Documentation**
   - Interactive docs: `http://localhost:8080/docs`
   - ReDoc: `http://localhost:8080/redoc`

#### API Endpoints

##### Health Check
```http
GET /
GET /health
```

##### Audio Transcription
```http
POST /transcribe/
Content-Type: multipart/form-data

Parameters:
- audio_file: Audio file (WAV, MP3, etc.)
- language: Language code (en-US, hi-IN, ta-IN, ml-IN)
```

##### Start Conversation
```http
POST /conversation/start
Content-Type: application/json

{
  "gemini_api_key": "your-api-key",
  "specialist": "AI/ML Specialist",
  "requirements": "I want to build a chatbot application"
}
```

##### Submit Answer
```http
POST /conversation/submit_answer
Content-Type: application/json

{
  "conversation_id": "uuid-string",
  "answer": "User's response to the question"
}
```

##### Conversation Management
```http
GET /conversation/{conversation_id}/status
DELETE /conversation/{conversation_id}
```

## 🎯 Specialist Types

The system supports the following specialist types:

- **AI/ML Specialist**: Machine learning and AI projects
- **Android Specialist**: Android mobile applications
- **iOS Specialist**: iOS mobile applications  
- **Full Stack Web Specialist**: Web applications
- **Game Development Specialist**: Game development projects
- **Data Science Specialist**: Data analytics and science projects

## 🔑 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Your Gemini API key | Required |
| `PORT` | Server port | 8080 |
| `ENVIRONMENT` | Environment name | production |
| `PYTHONUNBUFFERED` | Python output buffering | 1 |
| `PYTHONDONTWRITEBYTECODE` | Disable .pyc files | 1 |

## 📝 SRS Document Structure

The generated SRS follows industry standards with these sections:

1. **Introduction**
   - Purpose of the Document
   - Scope of the Project
   - Target Audience

2. **Overall Description**
   - Product Perspective
   - Product Functions
   - User Characteristics
   - Constraints
   - Assumptions and Dependencies

3. **System Features**
   - Detailed feature descriptions
   - Functional requirements

4. **Non-Functional Requirements**
   - Performance
   - Security
   - Usability
   - Reliability

5. **Appendices** (Optional)
   - Definitions and acronyms

## 🔒 Security Considerations

- API keys are handled securely and not logged
- Input validation on all endpoints
- CORS properly configured
- User sessions are temporary and cleaned up automatically
- No persistent storage of sensitive data

## 🚨 Error Handling

The system includes comprehensive error handling for:

- Invalid API keys
- Speech recognition failures
- Network connectivity issues
- Malformed requests
- Resource cleanup
- Timeout scenarios

## 🌍 Language Support

### Voice Input Languages

- **English (US)**: `en-US`
- **Hindi (India)**: `hi-IN`
- **Tamil (India)**: `ta-IN`
- **Malayalam (India)**: `ml-IN`

### Text-to-Speech

- Supports multiple languages for question narration
- Automatic language detection based on user selection

## 📊 Performance

- **Question Generation**: ~3-5 seconds per session
- **SRS Generation**: ~5-10 seconds depending on complexity
- **Memory Management**: Automatic cleanup of old conversations
- **Concurrent Users**: Supports multiple simultaneous sessions

## 🐛 Troubleshooting

### Common Issues

1. **Speech Recognition Not Working**
   - Check microphone permissions
   - Ensure stable internet connection
   - Try different audio formats

2. **API Key Issues**
   - Verify Gemini API key format (starts with 'AIza')
   - Check API quotas and billing
   - Ensure key has necessary permissions

3. **PDF Generation Fails**
   - Ensure `DejaVuSans.ttf` is in project directory
   - Check write permissions
   - Verify FPDF installation

4. **Docker Build Issues**
   - Ensure sufficient disk space
   - Check Docker daemon is running
   - Verify requirements.txt is complete

### Logs

- Application logs are available through standard Python logging
- Use `LOG_LEVEL=DEBUG` for detailed debugging
- API access logs available in FastAPI format

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request


## 🔄 Version History

- **v1.0.0**: Initial release with core functionality
  - Conversational SRS generation
  - Multi-language voice support
  - REST API and web interface
  - Docker containerization

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Review API documentation
3. Create an issue in the repository
4. Contact the development team

## 🙏 Acknowledgments

- Google Gemini AI for natural language processing
- LangChain for AI orchestration
- FastAPI for the REST API framework
- Streamlit for the web interface
- Contributors and testers

---

**Note**: This application requires an active internet connection for AI processing and speech recognition services. Ensure your Gemini API key has sufficient quota for the expected usage.
