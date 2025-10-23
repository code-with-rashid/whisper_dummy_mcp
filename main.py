# from src.new_whisper_mcp.server import mcp
from src.new_whisper_mcp.meeting_audio_mcp import mcp

if __name__ == "__main__":
    mcp.run(transport="sse", port=8000)
