from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.chatbot import stream_duggy_ai
import json

router = APIRouter()

@router.websocket("/ws/chat/ai/{user_id}")
async def duggy_private_chat(websocket: WebSocket, user_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                query = payload.get("query", "").strip()
            except json.JSONDecodeError:
                query = data.strip()
            
            if not query:
                continue

            # In a real app, you would pass the live scorecard state here.
            from app.services.state_manager import state_manager
            scorecard = await state_manager.get_scorecard()
            
            # Run toxicity moderation check
            from app.services.moderator import moderate_message
            mod_result = moderate_message(query)
            if mod_result.is_toxic:
                await websocket.send_text(f"🚫 Query blocked for toxicity: {mod_result.reason}")
                await websocket.send_text("[DONE]")
                continue


            # Stream response from our "Local/Hosted LLM"
            async for chunk in stream_duggy_ai(query, scorecard):
                await websocket.send_text(chunk)
                
            # Send a special token or signal to indicate message is complete
            await websocket.send_text("[DONE]")
            
    except WebSocketDisconnect:
        print(f"User {user_id} disconnected from private AI chat")
    except Exception as e:
        print(f"AI WebSocket Error: {e}")
