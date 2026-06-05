"""avatar_mcp.py — a self-contained MCP server for the Enigma Avatar.

Lets ANY MCP-capable AI (Claude, Odysseus, a custom agent, …) drive the on-screen
avatar. It talks to the avatar over the local bus (bus.py, ws://127.0.0.1:8765) —
no other Modkit pieces required. The overlay + bus must be running (Start-Avatar.ps1
or `python bus.py` + the Electron app); every tool is a safe no-op if they aren't.

Register in an MCP client (e.g. Claude Desktop / Code, Odysseus):
    command: python      args: ["<path>/avatar_mcp.py"]

Deps:  python -m pip install --user mcp websockets   (+ kokoro soundfile numpy for avatar_say)
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import websockets
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

ROOT = Path(__file__).resolve().parent
BUS = "ws://127.0.0.1:8765"
server = Server("enigma-avatar")


async def _send(cmd: dict) -> bool:
    """Send one JSON command to the avatar bus. Returns False if it isn't reachable."""
    try:
        async with websockets.connect(BUS, open_timeout=3) as ws:
            await ws.send(json.dumps(cmd))
        return True
    except Exception:
        return False


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="avatar_express",
            description="Make the on-screen avatar perform body language while you reply: talk, happy, wag, nod, shake, sad, alert.",
            inputSchema={"type": "object", "properties": {
                "emotion": {"type": "string", "description": "talk, happy, wag, nod, shake, sad, or alert"},
                "duration": {"type": "number", "description": "seconds to hold (default 2.5)"},
            }, "required": ["emotion"]},
        ),
        Tool(
            name="avatar_say",
            description="Make the avatar SPEAK text aloud (local Kokoro TTS) and lip-sync. Requires `kokoro` installed.",
            inputSchema={"type": "object", "properties": {
                "text": {"type": "string", "description": "what to say aloud"},
                "voice": {"type": "string", "description": "Kokoro voice id (af_heart, af_bella, am_adam, …)"},
                "speed": {"type": "number", "description": "0.5–2.0 (default 1.0)"},
            }, "required": ["text"]},
        ),
        Tool(
            name="avatar_command",
            description="Full avatar control, ONE action per call: load (url), size (value), moveTo (px,py), recolor (name,color), attach (url,bone), detach (id), springTune (stiffness/drag/gravity), stop.",
            inputSchema={"type": "object", "properties": {
                "action": {"type": "string"}, "url": {"type": "string"}, "value": {"type": "number"},
                "px": {"type": "number"}, "py": {"type": "number"}, "name": {"type": "string"},
                "color": {"type": "string"}, "bone": {"type": "string"}, "id": {"type": "string"},
            }, "required": ["action"]},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "avatar_express":
        ok = await _send({"action": "express", "name": arguments["emotion"], "dur": arguments.get("duration", 2.5)})
        return [TextContent(type="text", text=(f"avatar: expressed {arguments['emotion']!r}" if ok else "avatar: bus not reachable (is the overlay running?)"))]

    if name == "avatar_say":
        text = arguments["text"]
        try:
            from speak import synth   # vendored Kokoro TTS (tts.py) → WAV file
            wav = await asyncio.to_thread(synth, text, arguments.get("voice", "af_heart"), arguments.get("speed", 1.0))
            ok = await _send({"action": "say", "url": Path(wav).as_uri()})
            return [TextContent(type="text", text=(f"avatar: speaking ({len(text)} chars)" if ok else "avatar: synthesized, but bus not reachable"))]
        except Exception as e:
            return [TextContent(type="text", text=f"avatar_say failed (Kokoro installed? pip install --user kokoro): {e}")]

    if name == "avatar_command":
        cmd = {k: v for k, v in arguments.items() if v is not None}
        ok = await _send(cmd)
        return [TextContent(type="text", text=(f"avatar: {arguments.get('action')!r} sent" if ok else "avatar: bus not reachable"))]

    return [TextContent(type="text", text=f"unknown tool: {name}")]


async def _main():
    async with stdio_server() as (r, w):
        await server.run(r, w, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_main())
