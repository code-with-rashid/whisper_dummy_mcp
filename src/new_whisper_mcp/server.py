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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CHUNK_DURATION_SEC = 20  # seconds per chunk

NUM_CHUNKS = int(os.getenv("NUM_CHUNKS", "100"))

# Initialize FastMCP server
mcp = FastMCP("Mock Whisper MCP server")

def generate_random_text(length: int = 100) -> str:
    """Generate random text that mimics transcribed speech."""
    sentences = [
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
    ]
    
    text = ""
    while len(text) < length:
        text += random.choice(sentences) + " "
    return text[:length].strip()

async def download_audio(url: str) -> tuple[str, str]:
    """Download audio file from URL and return (file_path, content_type)."""
    logger.info(f"Downloading audio from {url}")
    async with httpx.AsyncClient(timeout=600) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "audio/mpeg")
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

async def transcribe_chunk(file_path: str, content_type: str | None) -> str:
    """Simulate transcription by returning random text."""
    logger.info(f"Transcribing chunk {file_path}")
    
    # Simulate API latency
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # Generate random transcription text
    text = generate_random_text(random.randint(80, 150))
    logger.info(f"Transcription result: {text[:50]}...")
    return text

async def transcribe_audio_generator(url: str) -> AsyncIterator[str]:
    """Helper generator for transcribing audio, yielding partial results."""
    logger.info(f"Starting transcription for {url}")
    tmp_file, content_type = await download_audio(url)
    try:
        chunks = await split_audio(tmp_file)
    finally:
        os.remove(tmp_file)

    for i, chunk in enumerate(chunks, 1):
        try:
            text = await transcribe_chunk(str(chunk), content_type)
            logger.info(f"Yielding chunk {i}/{len(chunks)} transcription: {text[:50]}...")
            yield text + " "
        except Exception as e:
            logger.error(f"Skipping chunk {chunk} due to error: {e}")
            yield f"[Error transcribing chunk {i}: {e}] "
        finally:
            os.remove(chunk)

@mcp.tool
async def transcribe_audio(url: str) -> str:
    """Transcribe audio from a given URL using mock Whisper API.
    
    Args:
        url: The URL of the audio file to transcribe.
    
    Returns:
        The full transcribed text from the audio (simulated with random text).
    """
    full_text = ""
    async for text in transcribe_audio_generator(url):
        logger.info(f"Collecting partial transcription: {text[:50]}...")
        full_text += text
    return full_text.strip()