"use client";

import { useState, useRef, useEffect } from "react";
import { Mic, MicOff, Radio } from "lucide-react";

type VoiceState = "idle" | "listening" | "thinking" | "speaking";

interface ChatTurn {
  user: string;
  agent: string;
}

export default function VoiceAgentPage() {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [isRecording, setIsRecording] = useState(false);
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [currentResponse, setCurrentResponse] = useState("");
  const [textInput, setTextInput] = useState("");

  const wsRef = useRef<WebSocket | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const animationFrameRef = useRef<number | null>(null);

  const API_HOST = process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL.replace("http", "ws")
    : "ws://localhost:8000";

  const transcriptRef = useRef(currentTranscript);

  useEffect(() => {
    transcriptRef.current = currentTranscript;
  }, [currentTranscript]);

  // Connect WebSocket on mount
  useEffect(() => {
    const ws = new WebSocket(`${API_HOST}/api/voice/ws`);
    wsRef.current = ws;

    ws.onopen = () => console.log("Voice WebSocket connected");
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "transcript") {
          setCurrentTranscript(data.user_text);
        } else if (data.type === "status") {
          setVoiceState(data.state as VoiceState);
        } else if (data.type === "llm_token") {
          setCurrentResponse((prev) => prev + data.token);
        } else if (data.type === "response_complete") {
          setCurrentResponse(data.full_text);
          if (data.audio_b64) {
            playBase64Audio(data.audio_b64);
          }
          setHistory((prev) => [...prev, { user: transcriptRef.current || "Voice Input", agent: data.full_text }]);
        }
      } catch (err) {
        console.error("WS message error", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [API_HOST]);

  // Audio Canvas visualizer loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let phase = 0;
    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      phase += 0.05;
      const baseRadius = 60;
      let radiusOffset = 0;

      if (voiceState === "listening") {
        radiusOffset = Math.sin(phase * 2) * 12;
      } else if (voiceState === "thinking") {
        radiusOffset = Math.sin(phase * 4) * 6;
      } else if (voiceState === "speaking") {
        radiusOffset = Math.sin(phase * 3) * 18;
      }

      ctx.beginPath();
      ctx.arc(centerX, centerY, baseRadius + radiusOffset, 0, Math.PI * 2);

      if (voiceState === "listening") {
        ctx.strokeStyle = "#10b981";
        ctx.fillStyle = "rgba(16, 185, 129, 0.15)";
      } else if (voiceState === "thinking") {
        ctx.strokeStyle = "#f59e0b";
        ctx.fillStyle = "rgba(245, 158, 11, 0.15)";
      } else if (voiceState === "speaking") {
        ctx.strokeStyle = "#6366f1";
        ctx.fillStyle = "rgba(99, 102, 241, 0.2)";
      } else {
        ctx.strokeStyle = "#6b7280";
        ctx.fillStyle = "rgba(107, 114, 128, 0.08)";
      }

      ctx.lineWidth = 4;
      ctx.stroke();
      ctx.fill();

      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();
    return () => {
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    };
  }, [voiceState]);

  const playBase64Audio = (b64Data: string) => {
    try {
      const audio = new Audio(`data:audio/mp3;base64,${b64Data}`);
      audio.play();
    } catch (e) {
      console.error("Audio playback error", e);
    }
  };

  const startMicRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = () => {
          const base64Audio = (reader.result as string).split(",")[1];
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            setCurrentResponse("");
            setVoiceState("thinking");
            wsRef.current.send(
              JSON.stringify({
                type: "audio_input",
                audio: base64Audio,
              })
            );
          }
        };
      };

      mediaRecorder.start();
      setIsRecording(true);
      setVoiceState("listening");
    } catch (err) {
      console.error("Microphone access denied", err);
    }
  };

  const stopMicRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleSendText = () => {
    if (!textInput.trim() || !wsRef.current) return;
    setCurrentTranscript(textInput);
    setCurrentResponse("");
    setVoiceState("thinking");

    wsRef.current.send(
      JSON.stringify({
        type: "audio_input",
        text: textInput,
      })
    );
    setTextInput("");
  };

  return (
    <div className="flex-1 p-6 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Radio className="w-6 h-6 text-primary animate-pulse" />
            <h1 className="text-2xl font-bold tracking-tight">Voice-to-Voice Real-Time Agent</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Low-latency spoken interaction with live Deepgram speech transcription & TTS.
          </p>
        </div>
      </div>

      {/* Central Visualizer Studio */}
      <div className="bg-card border rounded-2xl p-4 sm:p-8 flex flex-col items-center justify-center space-y-6 shadow-sm max-w-full overflow-hidden">
        <canvas ref={canvasRef} width={300} height={200} className="w-full max-w-[300px] h-[180px] sm:h-[200px]" />

        <div className="text-center space-y-1">
          <span className="text-xs uppercase tracking-wider font-semibold text-muted-foreground">
            Current Status
          </span>
          <div className="text-lg font-bold capitalize flex items-center justify-center gap-2">
            {voiceState === "listening" && <span className="text-emerald-500">🎙️ Listening...</span>}
            {voiceState === "thinking" && <span className="text-amber-500">🧠 Thinking...</span>}
            {voiceState === "speaking" && <span className="text-indigo-500">🔊 Speaking...</span>}
            {voiceState === "idle" && <span className="text-muted-foreground">Ready</span>}
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-center gap-4 w-full">
          {!isRecording ? (
            <button
              onClick={startMicRecording}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm rounded-full transition shadow-md min-h-[44px] w-full sm:w-auto"
            >
              <Mic className="w-5 h-5" /> Start Speaking
            </button>
          ) : (
            <button
              onClick={stopMicRecording}
              className="flex items-center justify-center gap-2 px-6 py-3 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-sm rounded-full transition shadow-md animate-bounce min-h-[44px] w-full sm:w-auto"
            >
              <MicOff className="w-5 h-5" /> Stop & Process
            </button>
          )}
        </div>

        {/* Text Fallback Input */}
        <div className="w-full max-w-md flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pt-4">
          <input
            type="text"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendText()}
            placeholder="Or type a spoken message..."
            className="flex-1 p-2.5 bg-background border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary min-h-[44px]"
          />
          <button
            onClick={handleSendText}
            className="px-5 py-2.5 bg-primary text-primary-foreground font-medium text-sm rounded-lg hover:opacity-90 transition min-h-[44px]"
          >
            Send
          </button>
        </div>
      </div>

      {/* Real-Time Transcript & History Display */}
      {(currentTranscript || currentResponse || history.length > 0) && (
        <div className="bg-card border rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground">Voice Dialogue History</h3>
          
          {history.map((turn, i) => (
            <div key={i} className="space-y-1 text-sm border-b border-border/30 pb-3 last:border-0 last:pb-0">
              <div className="text-foreground">
                <span className="font-semibold text-emerald-600">You: </span>
                {turn.user}
              </div>
              <div className="text-foreground">
                <span className="font-semibold text-indigo-600">Voice Agent: </span>
                {turn.agent}
              </div>
            </div>
          ))}

          {(currentTranscript || currentResponse) && (
            <div className="space-y-1 text-sm pt-2 border-t border-border/40">
              {currentTranscript && (
                <div className="text-foreground">
                  <span className="font-semibold text-emerald-600">You (Live): </span>
                  {currentTranscript}
                </div>
              )}
              {currentResponse && (
                <div className="text-foreground">
                  <span className="font-semibold text-indigo-600">Voice Agent (Live): </span>
                  {currentResponse}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
