from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
import speech_recognition as sr
from tool import generate_srs, generate_questions
import io
import uuid

app = FastAPI(
    title="Conversational SRS Generator API",
    description="An API to create Software Requirements Specifications through conversation.",
    version="1.0.0"
)

conversation_storage = {}

class StartConversationRequest(BaseModel):
    gemini_api_key: str
    specialist: str
    requirements: str

class SubmitAnswerRequest(BaseModel):
    conversation_id: str
    answer: str

@app.get("/", summary="Health Check")
async def root():
    return {"message": "Conversational SRS Generator API is running"}

@app.post("/transcribe/", summary="Transcribe Audio to Text")
async def transcribe_audio(
    language: str = Form("en-US"),
    audio_file: UploadFile = File(...)
):
    recognizer = sr.Recognizer()
    try:
        audio_bytes = await audio_file.read()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
        transcribed_text = recognizer.recognize_google(audio_data, language=language)
        return {"transcription": transcribed_text}
    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="Could not understand the audio.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.post("/conversation/start", summary="Start a New SRS Conversation")
async def start_conversation(request: StartConversationRequest):
    try:
        questions = generate_questions(
            api_key=request.gemini_api_key,
            specialist=request.specialist,
            requirements=request.requirements
        )
        if not questions:
            raise HTTPException(status_code=500, detail="Agent could not generate questions.")

        conversation_id = str(uuid.uuid4())
        conversation_storage[conversation_id] = {
            "gemini_api_key": request.gemini_api_key,
            "specialist": request.specialist,
            "history": [f"User's Initial Requirement: {request.requirements}"],
            "questions": questions,
            "question_index": 0
        }

        return {
            "conversation_id": conversation_id,
            "next_question": questions[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start conversation: {e}")


@app.post("/conversation/submit_answer", summary="Submit an Answer and Get Next Question")
async def submit_answer(request: SubmitAnswerRequest):
    convo_id = request.conversation_id
    if convo_id not in conversation_storage:
        raise HTTPException(status_code=404, detail="Conversation ID not found.")

    state = conversation_storage[convo_id]
    current_question_index = state["question_index"]
    current_question = state["questions"][current_question_index]

    state["history"].append(f"Agent Question: {current_question}")
    state["history"].append(f"User Answer: {request.answer}")
    state["question_index"] += 1

    if state["question_index"] < len(state["questions"]):
        next_question = state["questions"][state["question_index"]]
        return {
            "status": "in_progress",
            "conversation_id": convo_id,
            "next_question": next_question
        }
    else:
        full_conversation = "\n".join(state["history"])
        srs_document = generate_srs(
            api_key=state["gemini_api_key"],
            specialist=state["specialist"],
            conversation=full_conversation
        )
        del conversation_storage[convo_id]
        return {
            "status": "completed",
            "srs_document": srs_document
        }