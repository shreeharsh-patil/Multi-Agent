import base64
import json
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel

from src.config import settings
from src.services.llm import get_llm_provider
from src.utils.logger import logger

router = APIRouter(prefix="/api/voice", tags=["Voice"])


class SynthesizeRequest(BaseModel):
    text: str


_voice_client: httpx.AsyncClient | None = None


def _get_voice_client() -> httpx.AsyncClient:
    global _voice_client
    if _voice_client is None:
        _voice_client = httpx.AsyncClient(
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
    return _voice_client


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
        client = _get_voice_client()
        response = await client.post(
            "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
            content=content,
            headers=headers,
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
    """Synthesizes text into speech using Deepgram's Aura TTS model."""
    if not settings.deepgram_api_key:
        logger.error("Deepgram API Key is missing in settings.")
        raise HTTPException(status_code=400, detail="Deepgram API key is not configured on the server.")
    
    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": "application/json",
    }

    try:
        client = _get_voice_client()
        response = await client.post(
            "https://api.deepgram.com/v1/speak?model=aura-asteria-en",
            json={"text": req.text},
            headers=headers,
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


@router.websocket("/ws")
async def websocket_voice_agent(websocket: WebSocket):
    """Real-Time Voice-to-Voice WebSocket streaming endpoint.
    
    Exchanges bidirectional audio frames and text transcripts for low-latency
    voice interaction.
    """
    await websocket.accept()
    logger.info("Voice-to-Voice WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            msg_type = payload.get("type")

            if msg_type == "audio_input":
                # Process audio input payload (base64 audio)
                raw_audio_b64 = payload.get("audio", "")
                user_text = payload.get("text", "")

                if not user_text and raw_audio_b64 and settings.deepgram_api_key:
                    # Attempt transcription via Deepgram if key is present
                    try:
                        audio_bytes = base64.b64decode(raw_audio_b64)
                        client = _get_voice_client()
                        resp = await client.post(
                            "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
                            content=audio_bytes,
                            headers={
                                "Authorization": f"Token {settings.deepgram_api_key}",
                                "Content-Type": "audio/webm",
                            },
                        )
                        if resp.status_code == 200:
                            res_data = resp.json()
                            user_text = (
                                res_data.get("results", {})
                                .get("channels", [{}])[0]
                                .get("alternatives", [{}])[0]
                                .get("transcript", "")
                            )
                    except Exception as e:
                        logger.warning(f"WebSocket Deepgram transcription error: {e}")

                if not user_text:
                    user_text = payload.get("text", "Hello AI assistant")

                # Send user transcript back to client
                await websocket.send_json({
                    "type": "transcript",
                    "user_text": user_text,
                })

                # Notify thinking state
                await websocket.send_json({"type": "status", "state": "thinking"})

                # Generate LLM response stream
                llm = get_llm_provider()
                llm_response_chunks = []
                async for chunk in llm.generate_stream(
                    prompt=user_text,
                    system_instruction="You are a friendly, concise voice AI assistant. Keep responses brief (1-3 sentences) for natural speech synthesis.",
                ):
                    llm_response_chunks.append(chunk)
                    await websocket.send_json({
                        "type": "llm_token",
                        "token": chunk,
                    })

                full_llm_text = "".join(llm_response_chunks)

                # Notify speaking state
                await websocket.send_json({"type": "status", "state": "speaking"})

                # Attempt audio synthesis via Deepgram Aura
                audio_b64 = None
                if settings.deepgram_api_key:
                    try:
                        client = _get_voice_client()
                        tts_resp = await client.post(
                            "https://api.deepgram.com/v1/speak?model=aura-asteria-en",
                            json={"text": full_llm_text},
                            headers={
                                "Authorization": f"Token {settings.deepgram_api_key}",
                                "Content-Type": "application/json",
                            },
                        )
                        if tts_resp.status_code == 200:
                            audio_b64 = base64.b64encode(tts_resp.content).decode("utf-8")
                    except Exception as exc:
                        logger.warning(f"Deepgram TTS synthesis failed: {exc}")

                await websocket.send_json({
                    "type": "response_complete",
                    "full_text": full_llm_text,
                    "audio_b64": audio_b64,
                })

                await websocket.send_json({"type": "status", "state": "idle"})

    except WebSocketDisconnect:
        logger.info("Voice-to-Voice WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Error in Voice WebSocket stream: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
