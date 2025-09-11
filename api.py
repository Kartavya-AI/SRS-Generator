import os
import io
import uuid
import logging
import time
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import speech_recognition as sr
from tool import generate_srs, generate_questions
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

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

# Cloud Storage bucket
BUCKET_NAME = "srs-conversations"

# Create client with explicit project
storage_client = storage.Client()

class StartConversationRequest(BaseModel):
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

def save_conversation(conversation_id: str, data: dict):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"{conversation_id}.json")
    blob.upload_from_string(json.dumps(data), content_type='application/json')

def load_conversation(conversation_id: str) -> dict:
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"{conversation_id}.json")
    if not blob.exists():
        return None
    return json.loads(blob.download_as_text())

def delete_conversation(conversation_id: str):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(f"{conversation_id}.json")
    if blob.exists():
        blob.delete()
        
def get_secret_from_env(secret_name: str, default: Optional[str] = None) -> Optional[str]:
    return os.getenv(secret_name, default)

def get_gemini_api_key() -> str:
    """Get Gemini API key from environment variables"""
    api_key = get_secret_from_env("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Gemini API key not configured. Please set GEMINI_API_KEY environment variable."
        )
    return api_key

def validate_api_key(api_key: str) -> bool:
    return api_key and len(api_key) > 10 and api_key.startswith(('AIza', 'AIzaS'))

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
    # Check if Gemini API key is configured
    gemini_configured = bool(get_secret_from_env("GEMINI_API_KEY"))
    
    return {
        "status": "healthy",
        "active_conversations": len(conversation_storage),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "gemini_api_configured": gemini_configured
    }

@app.post("/conversation/start", response_model=ConversationStartResponse)
async def start_conversation(request: StartConversationRequest):
    if not request.specialist.strip():
        raise HTTPException(400, "Specialist field cannot be empty")
    if not request.requirements.strip():
        raise HTTPException(400, "Requirements field cannot be empty")

    gemini_api_key = get_gemini_api_key()
    if not validate_api_key(gemini_api_key):
        raise HTTPException(500, "Invalid Gemini API key configuration")

    # Generate questions
    questions = generate_questions(
        api_key=gemini_api_key,
        specialist=request.specialist,
        requirements=request.requirements
    )
    if not questions:
        raise HTTPException(500, "Unable to generate questions.")

    # Create conversation ID and save initial state
    conversation_id = str(uuid.uuid4())
    state = {
        "specialist": request.specialist,
        "history": [f"User's Initial Requirement: {request.requirements}"],
        "questions": questions,
        "question_index": 0,
        "created_at": time.time()
    }
    save_conversation(conversation_id, state)
    logger.info(f"Conversation {conversation_id} started with {len(questions)} questions.")

    return ConversationStartResponse(
        conversation_id=conversation_id,
        next_question=questions[0]
    )
    

@app.post("/conversation/submit_answer", response_model=SubmitAnswerResponse)
async def submit_answer(request: SubmitAnswerRequest):
    state = load_conversation(request.conversation_id)
    if state is None:
        raise HTTPException(404, "Conversation ID not found. Please start a new conversation.")
    if not request.answer.strip():
        raise HTTPException(400, "Answer cannot be empty")

    index = state["question_index"]
    question = state["questions"][index]

    # Record answer
    state["history"].append(f"Agent Question: {question}")
    state["history"].append(f"User Answer: {request.answer}")
    state["question_index"] += 1

    # Check if more questions remain
    if state["question_index"] < len(state["questions"]):
        save_conversation(request.conversation_id, state)
        next_question = state["questions"][state["question_index"]]
        return SubmitAnswerResponse(
            status="in_progress",
            conversation_id=request.conversation_id,
            next_question=next_question
        )
    else:
        # All questions answered - generate SRS
        gemini_api_key = get_gemini_api_key()
        full_conversation = "\n".join(state["history"])
        srs_document = generate_srs(
            api_key=gemini_api_key,
            specialist=state["specialist"],
            conversation=full_conversation
        )

        state["status"] = "completed"
        state["srs_document"] = srs_document
        save_conversation(request.conversation_id, state)

        return SubmitAnswerResponse(
            status="completed",
            conversation_id=request.conversation_id,
            next_question=None,
            srs_document=srs_document
        )
    

@app.get("/conversation/{conversation_id}/status")
async def conversation_status(conversation_id: str):
    state = load_conversation(conversation_id)
    if state is None:
        raise HTTPException(404, "Conversation not found")
    return {
        "conversation_id": conversation_id,
        "specialist": state["specialist"],
        "current_question_index": state["question_index"],
        "total_questions": len(state["questions"]),
        "progress": f"{state['question_index']}/{len(state['questions'])}",
        "status": state.get("status", "in_progress"),  # ✅ use stored status
        "srs_document": state.get("srs_document")
    }

@app.delete("/conversation/{conversation_id}")
async def cancel_conversation(conversation_id: str):
    state = load_conversation(conversation_id)
    if state is None:
        raise HTTPException(404, "Conversation not found")
    delete_conversation(conversation_id)
    return {"message": f"Conversation {conversation_id} has been cancelled"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
