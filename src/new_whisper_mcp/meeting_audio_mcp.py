import os
import tempfile
import asyncio
import logging
import random
import string
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
import httpx
from fastmcp import FastMCP
from typing import AsyncIterator

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_DURATION_SEC = 20
NUM_CHUNKS = int(os.getenv("NUM_CHUNKS", "100"))    

# -------------------------------------------------------------------------
# Initialize MCP
# -------------------------------------------------------------------------
mcp = FastMCP("Mock Meeting Audio MCP")

# -------------------------------------------------------------------------
# Mock data generation
# -------------------------------------------------------------------------
SAMPLE_SENTENCES = [
    "The quick brown fox jumps over the lazy dog.",
    "This is a sample transcription chunk.",
    "We are testing the mock audio transcription system.",
    "The weather today is quite pleasant.",
    "I enjoy working with language models.",
    "This mock server simulates Whisper API behavior.",
    "Audio transcription is becoming increasingly accurate.",
    "Machine learning has revolutionized speech recognition.",
    "Testing is an important part of development.",
    "This is a demonstration of the MCP pattern.",
    "Let's discuss the project timeline and deliverables.",
    "Can everyone please share their updates for this week?",
    "I think we should focus on the main objectives first.",
    "That's a great point, let me add to that.",
    "We need to make sure we hit all our targets.",
]

SPEAKERS = ["spk_1", "spk_2", "spk_3", "spk_4"]

def generate_random_text(length: int = 100) -> str:
    """Generate random text that mimics transcribed speech."""
    text = ""
    while len(text) < length:
        text += random.choice(SAMPLE_SENTENCES) + " "
    return text[:length].strip()

# -------------------------------------------------------------------------
# Utility functions
# -------------------------------------------------------------------------
async def download_audio(url: str) -> tuple[str, str]:
    """Download audio file from URL and return (file_path, content_type)."""
    logger.info(f"Downloading audio from {url}")
    async with httpx.AsyncClient(timeout=600) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type")
            parsed = urlparse(url)
            basename = Path(parsed.path).name or f"audio-{uuid4().hex}"
            suffix = Path(basename).suffix or ".mp3"

            with tempfile.NamedTemporaryFile(prefix="asr_", suffix=suffix, delete=False) as tmp_file:
                async for chunk in resp.aiter_bytes():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
    logger.info(f"Downloaded to {tmp_path}")
    return tmp_path, content_type

async def split_audio(input_path: str, chunk_len: int = CHUNK_DURATION_SEC) -> list[Path]:
    """Simulate splitting audio into smaller chunks."""
    logger.info(f"Splitting audio file {input_path}")
    tmp_dir = Path(tempfile.mkdtemp(prefix="audio_chunks_"))
    
    chunks = []
    for i in range(NUM_CHUNKS):
        chunk_path = tmp_dir / f"chunk_{i:03d}.mp3"
        chunk_path.touch()
        chunks.append(chunk_path)
    
    logger.info(f"Split into {len(chunks)} chunks")
    return chunks

async def transcribe_chunk(file_path: str, content_type: str | None) -> list[dict]:
    """Mock Whisper transcription returning detailed JSON with timestamps."""
    logger.info(f"Transcribing chunk {file_path}")
    
    # Simulate API latency
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # Generate mock segments with timestamps
    num_segments = random.randint(2, 5)
    segments = []
    current_time = 0.0
    
    for i in range(num_segments):
        start = round(current_time, 2)
        duration = round(random.uniform(2.0, 5.0), 2)
        end = round(start + duration, 2)
        
        text = generate_random_text(random.randint(60, 120))
        
        segments.append({
            "id": i,
            "seek": 0,
            "start": start,
            "end": end,
            "text": text,
            "tokens": [],
            "temperature": 0.0,
            "avg_logprob": -0.25,
            "compression_ratio": 1.2,
            "no_speech_prob": 0.001
        })
        
        current_time = end
    
    logger.info(f"Transcribed {file_path} successfully with {len(segments)} segments.")
    return segments

async def diarize_audio(file_path: str) -> list[dict]:
    """Mock diarization returning speaker segments."""
    logger.info(f"Calling mock diarization model for {file_path}")
    
    # Simulate API latency
    await asyncio.sleep(random.uniform(1.0, 2.0))
    
    # Generate mock diarization segments
    # Total duration: 100 chunks * 20 seconds = 2000 seconds
    total_duration = 2000.0
    num_segments = random.randint(30, 50)
    
    segments = []
    current_time = 0.0
    
    while current_time < total_duration and len(segments) < num_segments:
        speaker = random.choice(SPEAKERS)
        start = round(current_time, 2)
        duration = round(random.uniform(10.0, 80.0), 2)
        end = round(min(start + duration, total_duration), 2)
        
        segments.append({
            "speaker": speaker,
            "start": start,
            "end": end
        })
        
        current_time = end
    
    logger.info(f"Diarization result received with {len(segments)} segments.")
    return segments

def align_asr_with_diarization(asr_segments: list[dict], diar_segments: list[dict]) -> list[dict]:
    """Align Whisper ASR segments with diarization segments."""
    logger.info("Aligning ASR and diarization segments...")
    results = []
    
    for a in asr_segments:
        for d in diar_segments:
            overlap = (a["start"] <= d["end"]) and (a["end"] >= d["start"])
            if overlap:
                results.append({
                    "speaker": d["speaker"],
                    "start": round(a["start"], 2),
                    "end": round(a["end"], 2),
                    "text": a.get("text", "").strip()
                })
                break
    
    logger.info(f"Aligned {len(results)} ASR segments with speakers.")
    return results

# -------------------------------------------------------------------------
# Main MCP tool
# -------------------------------------------------------------------------
@mcp.tool
async def process_meeting_audio(url: str) -> dict:
    """
    Process meeting audio end-to-end:
    1. Download
    2. Transcribe with mock Whisper
    3. Mock Diarize
    4. Align speakers
    5. Return structured transcript
    """
    tmp_file, content_type = await download_audio(url)

    try:
        # 1️⃣ Transcribe full audio
        chunks = await split_audio(tmp_file)
        all_asr_segments = []
        offset = 0.0

        for chunk in chunks:
            segs = await transcribe_chunk(str(chunk), content_type)
            # adjust timestamps by offset
            for s in segs:
                s["start"] += offset
                s["end"] += offset
            all_asr_segments.extend(segs)
            # Simulate chunk duration (20 seconds)
            offset += CHUNK_DURATION_SEC
            os.remove(chunk)

        # 2️⃣ Diarize full audio
        diar_segments = await diarize_audio(tmp_file)

        # 3️⃣ Align
        aligned_segments = align_asr_with_diarization(all_asr_segments, diar_segments)

        # 4️⃣ Build final response
        full_text = " ".join([s["text"] for s in aligned_segments])
        speakers = sorted({s["speaker"] for s in aligned_segments})
        duration = max((s["end"] for s in aligned_segments), default=0.0)

        return {
            "meeting_id": str(uuid4()),
            "speakers": speakers,
            "segments": aligned_segments,
            "full_transcript": full_text,
            "duration": duration
        }

    finally:
        os.remove(tmp_file)