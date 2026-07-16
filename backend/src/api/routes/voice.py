from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
import httpx
from src.config import settings
from src.utils.logger import logger

router = APIRouter(prefix="/api/voice", tags=["Voice"])

class SynthesizeRequest(BaseModel):
    text: str

@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    """Transcribes an uploaded audio file using Deepgram's Nova-2 model."""
    if not settings.deepgram_api_key:
        logger.error("Deepgram API Key is missing in settings.")
        raise HTTPException(status_code=400, detail="Deepgram API key is not configured on the server.")
    
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read audio file: {str(e)}")

    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": file.content_type or "application/octet-stream",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
                content=content,
                headers=headers,
                timeout=60.0
            )
    except httpx.RequestError as exc:
        logger.error(f"HTTP request to Deepgram failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Network error communicating with Deepgram: {str(exc)}")

    if response.status_code != 200:
        logger.error(f"Deepgram responded with code {response.status_code}: {response.text}")
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Deepgram transcription failed: {response.text}"
        )
    
    try:
        data = response.json()
        transcript = (
            data.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
        )
        return {"transcript": transcript}
    except Exception as e:
        logger.error(f"Failed to parse Deepgram response: {e}")
        raise HTTPException(status_code=502, detail=f"Invalid response from Deepgram: {str(e)}")

@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    """Synthesizes text into speech using Deepgram's Aura text-to-speech model."""
    if not settings.deepgram_api_key:
        logger.error("Deepgram API Key is missing in settings.")
        raise HTTPException(status_code=400, detail="Deepgram API key is not configured on the server.")
    
    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepgram.com/v1/speak?model=aura-asteria-en",
                json={"text": req.text},
                headers=headers,
                timeout=60.0
            )
    except httpx.RequestError as exc:
        logger.error(f"HTTP request to Deepgram speak failed: {exc}")
        raise HTTPException(status_code=502, detail=f"Network error communicating with Deepgram Speak: {str(exc)}")

    if response.status_code != 200:
        logger.error(f"Deepgram Speak API responded with code {response.status_code}: {response.text}")
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Deepgram speech synthesis failed: {response.text}"
        )

    try:
        audio_data = response.content
        return Response(content=audio_data, media_type="audio/mpeg")
    except Exception as e:
        logger.error(f"Failed to read Deepgram audio response: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to read audio from Deepgram: {str(e)}")
