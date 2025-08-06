from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
import speech_recognition as sr
from tool import generate_srs
import io

app = FastAPI(
    title="SRS Generator API",
    description="An API to transcribe audio and generate Software Requirements Specifications.",
    version="1.0.0"
)

class SrsRequest(BaseModel):
    gemini_api_key: str
    specialist: str
    requirements: str

@app.get("/", summary="Health Check")
async def root():
    return {"message": "SRS Generator API is running"}

@app.post("/transcribe/", summary="Transcribe Audio to Text")
async def transcribe_audio(
    language: str = Form("en-US"), 
    audio_file: UploadFile = File(...)
):
    recognizer = sr.Recognizer()
    audio_bytes = await audio_file.read()
    
    try:
        with io.BytesIO(audio_bytes) as audio_source_bytes:
            with sr.AudioFile(audio_source_bytes) as source:
                audio_data = recognizer.record(source)
            transcribed_text = recognizer.recognize_google(audio_data, language=language)
            return {"transcription": transcribed_text}

    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="Could not understand the audio.")
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Speech recognition service error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@app.post("/generate-srs/", summary="Generate SRS Document")
async def create_srs(request: SrsRequest):
    try:
        srs_document = generate_srs(
            api_key=request.gemini_api_key,
            specialist=request.specialist,
            requirements=request.requirements
        )
        return {"srs_document": srs_document}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate SRS document: {e}")