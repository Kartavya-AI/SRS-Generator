import os
import io
import uuid
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import speech_recognition as sr
from tool import generate_srs, generate_questions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Conversational SRS Generator API",
    description="An API to create Software Requirements Specifications through conversation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conversation_storage = {}

class StartConversationRequest(BaseModel):
    gemini_api_key: str
    specialist: str
    requirements: str

class SubmitAnswerRequest(BaseModel):
    conversation_id: str
    answer: str

class TranscriptionResponse(BaseModel):
    transcription: str

class ConversationStartResponse(BaseModel):
    conversation_id: str
    next_question: str

class SubmitAnswerResponse(BaseModel):
    status: str
    conversation_id: Optional[str] = None
    next_question: Optional[str] = None
    srs_document: Optional[str] = None

def get_secret_from_env(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(secret_name, default)

def validate_api_key(api_key: str) -> bool:
    return api_key and len(api_key) > 10 and api_key.startswith(('AIza', 'AIzaS'))

def cleanup_conversation_storage():
    if len(conversation_storage) > 100:
        oldest_keys = list(conversation_storage.keys())[:-50]
        for key in oldest_keys:
            conversation_storage.pop(key, None)
        logger.info(f"Cleaned up {len(oldest_keys)} old conversations")

@app.get("/", summary="Health Check")
async def root():
    return {
        "message": "Conversational SRS Generator API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health", summary="Detailed Health Check")
async def health_check():
    """Detailed health check with system information"""
    return {
        "status": "healthy",
        "active_conversations": len(conversation_storage),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
    }

@app.post("/transcribe/", summary="Transcribe Audio to Text", response_model=TranscriptionResponse)
async def transcribe_audio(
    language: str = Form("en-US", description="Language code for transcription"),
    audio_file: UploadFile = File(..., description="Audio file to transcribe")
):
    recognizer = sr.Recognizer()
    
    try:
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            logger.warning(f"Invalid file type: {audio_file.content_type}")
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Please upload an audio file."
            )
        
        audio_bytes = await audio_file.read()
        logger.info(f"Processing audio file: {audio_file.filename}, size: {len(audio_bytes)} bytes")
        
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        
        transcribed_text = recognizer.recognize_google(audio_data, language=language)
        logger.info(f"Successfully transcribed audio: {transcribed_text[:50]}...")
        return TranscriptionResponse(transcription=transcribed_text)
        
    except sr.UnknownValueError:
        logger.error("Speech recognition could not understand the audio")
        raise HTTPException(
            status_code=400, 
            detail="Could not understand the audio. Please ensure clear speech and proper audio quality."
        )
    except sr.RequestError as e:
        logger.error(f"Speech recognition service error: {e}")
        raise HTTPException(
            status_code=503, 
            detail="Speech recognition service is currently unavailable. Please try again later."
        )
    except Exception as e:
        logger.error(f"Unexpected error during transcription: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred during transcription: {str(e)}"
        )

@app.post("/conversation/start", 
          summary="Start a New SRS Conversation",
          response_model=ConversationStartResponse)
async def start_conversation(request: StartConversationRequest):
    try:
        if not validate_api_key(request.gemini_api_key):
            raise HTTPException(
                status_code=400,
                detail="Invalid Gemini API key format"
            )
        
        if not request.specialist.strip():
            raise HTTPException(
                status_code=400,
                detail="Specialist field cannot be empty"
            )
        
        if not request.requirements.strip():
            raise HTTPException(
                status_code=400,
                detail="Requirements field cannot be empty"
            )
        
        logger.info(f"Starting conversation for specialist: {request.specialist}")
        
        questions = generate_questions(
            api_key=request.gemini_api_key,
            specialist=request.specialist,
            requirements=request.requirements
        )
        
        if not questions or len(questions) == 0:
            logger.error("AI agent could not generate questions")
            raise HTTPException(
                status_code=500, 
                detail="Unable to generate questions. Please check your requirements and try again."
            )
        
        cleanup_conversation_storage()
        
        # Create conversation session
        conversation_id = str(uuid.uuid4())
        conversation_storage[conversation_id] = {
            "gemini_api_key": request.gemini_api_key,
            "specialist": request.specialist,
            "history": [f"User's Initial Requirement: {request.requirements}"],
            "questions": questions,
            "question_index": 0,
            "created_at": os.time.time() if hasattr(os, 'time') else 0
        }
        
        logger.info(f"Created conversation {conversation_id} with {len(questions)} questions")
        
        return ConversationStartResponse(
            conversation_id=conversation_id,
            next_question=questions[0]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start conversation: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to start conversation: {str(e)}"
        )

@app.post("/conversation/submit_answer", 
          summary="Submit an Answer and Get Next Question",
          response_model=SubmitAnswerResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """
    Submit an answer to the current question and get the next question,
    or generate the final SRS document if all questions are answered.
    """
    try:
        # Validate conversation ID
        if not request.conversation_id or request.conversation_id not in conversation_storage:
            raise HTTPException(
                status_code=404, 
                detail="Conversation ID not found. Please start a new conversation."
            )
        
        # Validate answer
        if not request.answer.strip():
            raise HTTPException(
                status_code=400,
                detail="Answer cannot be empty"
            )
        
        # Get conversation state
        state = conversation_storage[request.conversation_id]
        current_question_index = state["question_index"]
        current_question = state["questions"][current_question_index]
        
        # Record the conversation
        state["history"].append(f"Agent Question: {current_question}")
        state["history"].append(f"User Answer: {request.answer}")
        state["question_index"] += 1
        
        logger.info(f"Conversation {request.conversation_id}: Answer {current_question_index + 1}/{len(state['questions'])}")
        
        # Check if more questions remain
        if state["question_index"] < len(state["questions"]):
            # More questions remain
            next_question = state["questions"][state["question_index"]]
            return SubmitAnswerResponse(
                status="in_progress",
                conversation_id=request.conversation_id,
                next_question=next_question
            )
        else:
            # All questions answered - generate SRS document
            logger.info(f"Generating SRS document for conversation {request.conversation_id}")
            
            full_conversation = "\n".join(state["history"])
            
            try:
                srs_document = generate_srs(
                    api_key=state["gemini_api_key"],
                    specialist=state["specialist"],
                    conversation=full_conversation
                )
                
                # Clean up the conversation from memory
                del conversation_storage[request.conversation_id]
                
                logger.info(f"Successfully generated SRS document for conversation {request.conversation_id}")
                
                return SubmitAnswerResponse(
                    status="completed",
                    srs_document=srs_document
                )
                
            except Exception as e:
                logger.error(f"Failed to generate SRS document: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate SRS document: {str(e)}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in submit_answer: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred: {str(e)}"
        )

# Conversation management endpoints
@app.get("/conversation/{conversation_id}/status", summary="Get Conversation Status")
async def get_conversation_status(conversation_id: str):
    """Get the current status of a conversation"""
    if conversation_id not in conversation_storage:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    state = conversation_storage[conversation_id]
    return {
        "conversation_id": conversation_id,
        "specialist": state["specialist"],
        "current_question_index": state["question_index"],
        "total_questions": len(state["questions"]),
        "progress": f"{state['question_index']}/{len(state['questions'])}",
        "status": "completed" if state["question_index"] >= len(state["questions"]) else "in_progress"
    }

@app.delete("/conversation/{conversation_id}", summary="Cancel Conversation")
async def cancel_conversation(conversation_id: str):
    """Cancel and delete a conversation"""
    if conversation_id not in conversation_storage:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del conversation_storage[conversation_id]
    return {"message": f"Conversation {conversation_id} has been cancelled"}

# Error handlers
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {str(exc)}")
    return {
        "error": "Internal server error",
        "message": "An unexpected error occurred. Please try again later."
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("SRS Generator API starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'production')}")
    logger.info("API is ready to serve requests")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("SRS Generator API shutting down...")
    # Clean up resources if needed
    conversation_storage.clear()
    logger.info("Cleanup completed")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)