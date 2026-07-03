import os
import json
import asyncio
from typing import Dict, List, Set, Optional
from fastapi import WebSocket
import redis.asyncio as aioredis

from app.models import DRSState, MomentThread
from app.config import USE_REDIS, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

# Default fallback initial state
DEFAULT_SCORECARD = {
    "batting_team": "CSK",
    "bowling_team": "MI",
    "runs": 164,
    "wickets": 4,
    "overs": "17.2",
    "target": 192,
    "recent_balls": ["4", "0", "6", "W", "1", "2"],
    "batsman_striker": "Ruturaj Gaikwad: 76*(42)",
    "bowler_active": "Jasprit Bumrah: 3.2-0-28-2",
    "excitement_csk": 62,
    "excitement_mi": 38
}

DEFAULT_FANTASY_TEAMS = {
    "user_team": {
        "name": "Indra's Dream Team",
        "captain": "Ruturaj Gaikwad",
        "players": {
            "Ruturaj Gaikwad": {"role": "Batsman", "points": 92},
            "MS Dhoni": {"role": "Wicketkeeper", "points": 0},
            "Ravindra Jadeja": {"role": "All-Rounder", "points": 10}
        },
        "total_points": 102
    },
    "challenger_team": {
        "name": "Challenger XI",
        "captain": "Jasprit Bumrah",
        "players": {
            "Jasprit Bumrah": {"role": "Bowler", "points": 54},
            "Rohit Sharma": {"role": "Batsman", "points": 0},
            "Hardik Pandya": {"role": "All-Rounder", "points": 0}
        },
        "total_points": 54
    }
}

DEFAULT_MOCK_THREADS = [
    {
        "id": "mock-thread-1",
        "title": "🔥 Gaikwad hits Bumrah for SIX!",
        "description": "Over 15.2: Gaikwad picks the length early and dispatches it over deep mid-wicket. Spectacular shot! CSK in charge?",
        "over": "15.2",
        "event_type": "boundary",
        "timestamp": "08:10 PM",
        "replies": []
    },
    {
        "id": "mock-thread-2",
        "title": "💥 WICKET! Dube clean bowled!",
        "description": "Over 16.4: Bumrah bowls an absolute peach of a yorker! Stumps shattered. MI fighting back!",
        "over": "16.4",
        "event_type": "wicket",
        "timestamp": "08:24 PM",
        "replies": []
    }
]

class BaseStateManager:
    def __init__(self):
        self.active_sockets: Dict[str, Set[WebSocket]] = {
            "csk": set(),
            "mi": set(),
            "neutral": set()
        }

    async def get_fan_counts(self) -> dict:
        return {
            "csk": max(12, len(self.active_sockets.get("csk", set())) + 12),
            "mi": max(8, len(self.active_sockets.get("mi", set())) + 8),
            "neutral": max(5, len(self.active_sockets.get("neutral", set())) + 5)
        }

    async def broadcast_fan_counts(self):
        counts = await self.get_fan_counts()
        if hasattr(self, "broadcast_to_all"):
            await self.broadcast_to_all({
                "type": "fan_counts",
                "counts": counts
            })

    async def register_socket(self, stand_id: str, websocket: WebSocket):
        if stand_id in self.active_sockets:
            self.active_sockets[stand_id].add(websocket)
            await self.broadcast_fan_counts()

    async def unregister_socket(self, stand_id: str, websocket: WebSocket):
        if stand_id in self.active_sockets and websocket in self.active_sockets[stand_id]:
            self.active_sockets[stand_id].remove(websocket)
            await self.broadcast_fan_counts()

    async def local_broadcast(self, stand_id: str, payload: dict):
        """Sends a payload directly to locally connected websockets in a stand."""
        sockets = self.active_sockets.get(stand_id, set())
        if not sockets:
            return
        disconnected = set()
        for websocket in sockets:
            try:
                await websocket.send_text(json.dumps(payload))
            except Exception:
                disconnected.add(websocket)
        for ws in disconnected:
            if ws in sockets:
                sockets.remove(ws)

    async def get_fantasy_teams(self) -> dict:
        raise NotImplementedError()

    async def update_fantasy_points(self, batsman: str, bowler: str, runs: int, event_type: str) -> dict:
        raise NotImplementedError()


class InMemoryStateManager(BaseStateManager):
    def __init__(self):
        super().__init__()
        self._scorecard = dict(DEFAULT_SCORECARD)
        self._drs_state = DRSState()
        self._moment_threads: List[MomentThread] = [MomentThread.model_validate(t) for t in DEFAULT_MOCK_THREADS]
        self._moderator_logs: List[dict] = []
        self._fantasy_teams = json.loads(json.dumps(DEFAULT_FANTASY_TEAMS))
        self._lock = asyncio.Lock()

    async def get_scorecard(self) -> dict:
        async with self._lock:
            return dict(self._scorecard)

    async def update_scorecard(self, updates: dict) -> dict:
        async with self._lock:
            self._scorecard.update(updates)
            return dict(self._scorecard)

    async def get_drs(self) -> DRSState:
        async with self._lock:
            return self._drs_state

    async def start_drs(self, batsman: str, bowler: str, over: str) -> DRSState:
        async with self._lock:
            self._drs_state = DRSState(
                batsman=batsman,
                bowler=bowler,
                over=over,
                is_active=True,
                votes_out=0,
                votes_not_out=0,
                time_remaining=15,
                official_verdict=None
            )
            return self._drs_state

    async def cast_drs_vote(self, vote: str) -> DRSState:
        async with self._lock:
            if self._drs_state.is_active:
                if vote == "OUT":
                    self._drs_state.votes_out += 1
                elif vote == "NOT_OUT":
                    self._drs_state.votes_not_out += 1
            return self._drs_state

    async def tick_drs(self) -> DRSState:
        async with self._lock:
            if self._drs_state.is_active and self._drs_state.time_remaining > 0:
                self._drs_state.time_remaining -= 1
            return self._drs_state

    async def resolve_drs(self, official_verdict: str) -> DRSState:
        async with self._lock:
            self._drs_state.official_verdict = official_verdict
            self._drs_state.is_active = False
            return self._drs_state

    async def get_threads(self) -> List[MomentThread]:
        async with self._lock:
            return list(self._moment_threads)

    async def add_thread(self, thread: MomentThread):
        async with self._lock:
            self._moment_threads.insert(0, thread)

    async def get_moderator_logs(self) -> List[dict]:
        async with self._lock:
            return list(self._moderator_logs)

    async def add_moderator_log(self, log: dict):
        async with self._lock:
            self._moderator_logs.append(log)

    async def get_fantasy_teams(self) -> dict:
        async with self._lock:
            return self._fantasy_teams

    async def update_fantasy_points(self, batsman: str, bowler: str, runs: int, event_type: str) -> dict:
        async with self._lock:
            user_team = self._fantasy_teams["user_team"]
            challenger_team = self._fantasy_teams["challenger_team"]
            
            # Helper to calculate points earned on this delivery
            def process_player(player_name, is_captain, is_batsman, is_bowler):
                pts = 0
                if is_batsman:
                    pts += runs * 1
                    if runs == 4:
                        pts += 1
                    elif runs == 6:
                        pts += 2
                    if event_type == "wicket":
                        pts -= 20
                if is_bowler:
                    if event_type == "wicket":
                        pts += 25
                    elif runs == 0:
                        pts += 1
                return pts * 2 if is_captain else pts

            # Update user team (Indra's Dream Team)
            for name, details in user_team["players"].items():
                is_captain = (name == user_team["captain"])
                pts_earned = process_player(name, is_captain, name == batsman, name == bowler)
                details["points"] += pts_earned

            # Update challenger team (Challenger XI)
            for name, details in challenger_team["players"].items():
                is_captain = (name == challenger_team["captain"])
                pts_earned = process_player(name, is_captain, name == batsman, name == bowler)
                details["points"] += pts_earned

            # Re-sum points
            user_team["total_points"] = sum(p["points"] for p in user_team["players"].values())
            challenger_team["total_points"] = sum(p["points"] for p in challenger_team["players"].values())

            # Broadcast update
            await self.broadcast_to_all({
                "type": "fantasy_update",
                "teams": self._fantasy_teams
            })
            return self._fantasy_teams

    async def broadcast_to_stand(self, stand_id: str, payload: dict):
        await self.local_broadcast(stand_id, payload)

    async def broadcast_to_all(self, payload: dict):
        for stand in self.active_sockets.keys():
            await self.local_broadcast(stand, payload)


class RedisStateManager(BaseStateManager):
    def __init__(self):
        super().__init__()
        self.redis_client: Optional[aioredis.Redis] = None
        self.pubsub_task: Optional[asyncio.Task] = None
        self._scorecard = dict(DEFAULT_SCORECARD)
        self._drs_state = DRSState()
        self._moment_threads: List[MomentThread] = [MomentThread.model_validate(t) for t in DEFAULT_MOCK_THREADS]
        self._moderator_logs: List[dict] = []
        self._fantasy_teams = json.loads(json.dumps(DEFAULT_FANTASY_TEAMS))
        self._local_lock = asyncio.Lock()

    async def initialize(self):
        try:
            self.redis_client = aioredis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD if REDIS_PASSWORD else None,
                decode_responses=True
            )
            # Ping test
            await self.redis_client.ping()
            
            # Hydrate Redis keys with default states if not present
            if not await self.redis_client.exists("dugout:scorecard"):
                await self.redis_client.hset("dugout:scorecard", mapping={k: json.dumps(v) for k, v in DEFAULT_SCORECARD.items()})

            if not await self.redis_client.exists("dugout:threads"):
                for thread in reversed(DEFAULT_MOCK_THREADS):
                    await self.redis_client.lpush("dugout:threads", json.dumps(thread))

            if not await self.redis_client.exists("dugout:fantasy"):
                await self.redis_client.set("dugout:fantasy", json.dumps(DEFAULT_FANTASY_TEAMS))

            # Start background pub/sub listener
            self.pubsub_task = asyncio.create_task(self._listen_for_broadcasts())
            print("Successfully initialized Redis connection and listener task.")
        except Exception as e:
            print(f"Redis initialization failed: {e}. Falling back to in-memory mode internally.")
            self.redis_client = None

    async def get_scorecard(self) -> dict:
        if not self.redis_client:
            async with self._local_lock:
                return dict(self._scorecard)
        try:
            data = await self.redis_client.hgetall("dugout:scorecard")
            if not data:
                return dict(DEFAULT_SCORECARD)
            return {k: json.loads(v) for k, v in data.items()}
        except Exception as e:
            print(f"Redis get_scorecard error: {e}")
            async with self._local_lock:
                return dict(self._scorecard)

    async def update_scorecard(self, updates: dict) -> dict:
        if not self.redis_client:
            async with self._local_lock:
                self._scorecard.update(updates)
                return dict(self._scorecard)
        try:
            await self.redis_client.hset(
                "dugout:scorecard",
                mapping={k: json.dumps(v) for k, v in updates.items()}
            )
            return await self.get_scorecard()
        except Exception as e:
            print(f"Redis update_scorecard error: {e}")
            async with self._local_lock:
                self._scorecard.update(updates)
                return dict(self._scorecard)

    async def get_drs(self) -> DRSState:
        if not self.redis_client:
            async with self._local_lock:
                return self._drs_state
        try:
            data = await self.redis_client.get("dugout:drs")
            if not data:
                return DRSState()
            return DRSState.model_validate_json(data)
        except Exception as e:
            print(f"Redis get_drs error: {e}")
            async with self._local_lock:
                return self._drs_state

    async def start_drs(self, batsman: str, bowler: str, over: str) -> DRSState:
        state = DRSState(
            batsman=batsman,
            bowler=bowler,
            over=over,
            is_active=True,
            votes_out=0,
            votes_not_out=0,
            time_remaining=15,
            official_verdict=None
        )
        if not self.redis_client:
            async with self._local_lock:
                self._drs_state = state
                return self._drs_state
        try:
            await self.redis_client.set("dugout:drs", state.model_dump_json())
            return state
        except Exception as e:
            print(f"Redis start_drs error: {e}")
            async with self._local_lock:
                self._drs_state = state
                return self._drs_state

    async def cast_drs_vote(self, vote: str) -> DRSState:
        if not self.redis_client:
            async with self._local_lock:
                if self._drs_state.is_active:
                    if vote == "OUT":
                        self._drs_state.votes_out += 1
                    elif vote == "NOT_OUT":
                        self._drs_state.votes_not_out += 1
                return self._drs_state
        try:
            # We fetch state, update it atomically using redis locks or basic get/set
            # In production, concurrent updates are done using transactional pipelines or lua script
            # Here we will parse, increment counter in redis, and write back
            data = await self.redis_client.get("dugout:drs")
            if data:
                state = DRSState.model_validate_json(data)
                if state.is_active:
                    if vote == "OUT":
                        state.votes_out += 1
                    elif vote == "NOT_OUT":
                        state.votes_not_out += 1
                    await self.redis_client.set("dugout:drs", state.model_dump_json())
                    return state
            return DRSState()
        except Exception as e:
            print(f"Redis cast_drs_vote error: {e}")
            async with self._local_lock:
                if self._drs_state.is_active:
                    if vote == "OUT":
                        self._drs_state.votes_out += 1
                    elif vote == "NOT_OUT":
                        self._drs_state.votes_not_out += 1
                return self._drs_state

    async def tick_drs(self) -> DRSState:
        if not self.redis_client:
            async with self._local_lock:
                if self._drs_state.is_active and self._drs_state.time_remaining > 0:
                    self._drs_state.time_remaining -= 1
                return self._drs_state
        try:
            data = await self.redis_client.get("dugout:drs")
            if data:
                state = DRSState.model_validate_json(data)
                if state.is_active and state.time_remaining > 0:
                    state.time_remaining -= 1
                    await self.redis_client.set("dugout:drs", state.model_dump_json())
                    return state
            return DRSState()
        except Exception as e:
            print(f"Redis tick_drs error: {e}")
            async with self._local_lock:
                if self._drs_state.is_active and self._drs_state.time_remaining > 0:
                    self._drs_state.time_remaining -= 1
                return self._drs_state

    async def resolve_drs(self, official_verdict: str) -> DRSState:
        if not self.redis_client:
            async with self._local_lock:
                self._drs_state.official_verdict = official_verdict
                self._drs_state.is_active = False
                return self._drs_state
        try:
            data = await self.redis_client.get("dugout:drs")
            if data:
                state = DRSState.model_validate_json(data)
                state.official_verdict = official_verdict
                state.is_active = False
                await self.redis_client.set("dugout:drs", state.model_dump_json())
                return state
            return DRSState()
        except Exception as e:
            print(f"Redis resolve_drs error: {e}")
            async with self._local_lock:
                self._drs_state.official_verdict = official_verdict
                self._drs_state.is_active = False
                return self._drs_state

    async def get_threads(self) -> List[MomentThread]:
        if not self.redis_client:
            async with self._local_lock:
                return list(self._moment_threads)
        try:
            items = await self.redis_client.lrange("dugout:threads", 0, -1)
            return [MomentThread.model_validate_json(item) for item in items]
        except Exception as e:
            print(f"Redis get_threads error: {e}")
            async with self._local_lock:
                return list(self._moment_threads)

    async def add_thread(self, thread: MomentThread):
        if not self.redis_client:
            async with self._local_lock:
                self._moment_threads.insert(0, thread)
                return
        try:
            await self.redis_client.lpush("dugout:threads", thread.model_dump_json())
        except Exception as e:
            print(f"Redis add_thread error: {e}")
            async with self._local_lock:
                self._moment_threads.insert(0, thread)

    async def get_moderator_logs(self) -> List[dict]:
        if not self.redis_client:
            async with self._local_lock:
                return list(self._moderator_logs)
        try:
            items = await self.redis_client.lrange("dugout:logs", 0, -1)
            return [json.loads(item) for item in items]
        except Exception as e:
            print(f"Redis get_moderator_logs error: {e}")
            async with self._local_lock:
                return list(self._moderator_logs)

    async def add_moderator_log(self, log: dict):
        if not self.redis_client:
            async with self._local_lock:
                self._moderator_logs.append(log)
                return
        try:
            await self.redis_client.lpush("dugout:logs", json.dumps(log))
        except Exception as e:
            print(f"Redis add_moderator_log error: {e}")
            async with self._local_lock:
                self._moderator_logs.append(log)

    async def get_fantasy_teams(self) -> dict:
        if not self.redis_client:
            async with self._local_lock:
                return self._fantasy_teams
        try:
            data = await self.redis_client.get("dugout:fantasy")
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis get_fantasy_teams error: {e}")
        async with self._local_lock:
            return self._fantasy_teams

    async def update_fantasy_points(self, batsman: str, bowler: str, runs: int, event_type: str) -> dict:
        def process_player(player_name, is_captain, is_batsman, is_bowler):
            pts = 0
            if is_batsman:
                pts += runs * 1
                if runs == 4:
                    pts += 1
                elif runs == 6:
                    pts += 2
                if event_type == "wicket":
                    pts -= 20
            if is_bowler:
                if event_type == "wicket":
                    pts += 25
                elif runs == 0:
                    pts += 1
            return pts * 2 if is_captain else pts

        if not self.redis_client:
            async with self._local_lock:
                user_team = self._fantasy_teams["user_team"]
                challenger_team = self._fantasy_teams["challenger_team"]
                for name, details in user_team["players"].items():
                    is_captain = (name == user_team["captain"])
                    details["points"] += process_player(name, is_captain, name == batsman, name == bowler)
                for name, details in challenger_team["players"].items():
                    is_captain = (name == challenger_team["captain"])
                    details["points"] += process_player(name, is_captain, name == batsman, name == bowler)
                user_team["total_points"] = sum(p["points"] for p in user_team["players"].values())
                challenger_team["total_points"] = sum(p["points"] for p in challenger_team["players"].values())
                await self.broadcast_to_all({
                    "type": "fantasy_update",
                    "teams": self._fantasy_teams
                })
                return self._fantasy_teams

        try:
            data = await self.redis_client.get("dugout:fantasy")
            teams = json.loads(data) if data else json.loads(json.dumps(DEFAULT_FANTASY_TEAMS))
            user_team = teams["user_team"]
            challenger_team = teams["challenger_team"]
            for name, details in user_team["players"].items():
                is_captain = (name == user_team["captain"])
                details["points"] += process_player(name, is_captain, name == batsman, name == bowler)
            for name, details in challenger_team["players"].items():
                is_captain = (name == challenger_team["captain"])
                details["points"] += process_player(name, is_captain, name == batsman, name == bowler)
            user_team["total_points"] = sum(p["points"] for p in user_team["players"].values())
            challenger_team["total_points"] = sum(p["points"] for p in challenger_team["players"].values())
            await self.redis_client.set("dugout:fantasy", json.dumps(teams))
            await self.broadcast_to_all({
                "type": "fantasy_update",
                "teams": teams
            })
            return teams
        except Exception as e:
            print(f"Redis update_fantasy_points error: {e}")

        async with self._local_lock:
            user_team = self._fantasy_teams["user_team"]
            challenger_team = self._fantasy_teams["challenger_team"]
            for name, details in user_team["players"].items():
                is_captain = (name == user_team["captain"])
                details["points"] += process_player(name, is_captain, name == batsman, name == bowler)
            for name, details in challenger_team["players"].items():
                is_captain = (name == challenger_team["captain"])
                details["points"] += process_player(name, is_captain, name == batsman, name == bowler)
            user_team["total_points"] = sum(p["points"] for p in user_team["players"].values())
            challenger_team["total_points"] = sum(p["points"] for p in challenger_team["players"].values())
            await self.broadcast_to_all({
                "type": "fantasy_update",
                "teams": self._fantasy_teams
            })
            return self._fantasy_teams

    async def broadcast_to_stand(self, stand_id: str, payload: dict):
        if not self.redis_client:
            await self.local_broadcast(stand_id, payload)
            return
        try:
            # Publish to Redis channel
            channel_name = f"dugout:broadcast:{stand_id}"
            await self.redis_client.publish(channel_name, json.dumps(payload))
        except Exception as e:
            print(f"Redis publish error: {e}. Broadcasting locally.")
            await self.local_broadcast(stand_id, payload)

    async def broadcast_to_all(self, payload: dict):
        if not self.redis_client:
            for stand in self.active_sockets.keys():
                await self.local_broadcast(stand, payload)
            return
        try:
            for stand in self.active_sockets.keys():
                channel_name = f"dugout:broadcast:{stand}"
                await self.redis_client.publish(channel_name, json.dumps(payload))
        except Exception as e:
            print(f"Redis publish all error: {e}. Broadcasting locally.")
            for stand in self.active_sockets.keys():
                await self.local_broadcast(stand, payload)

    async def _listen_for_broadcasts(self):
        """Background task running on each server to listen to Redis Pub/Sub channels."""
        pubsub = self.redis_client.pubsub()
        channels = [f"dugout:broadcast:{stand}" for stand in self.active_sockets.keys()]
        await pubsub.subscribe(*channels)
        
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    channel = message["channel"]
                    stand_id = channel.split(":")[-1]
                    payload = json.loads(message["data"])
                    # Send payload to locally connected websockets
                    await self.local_broadcast(stand_id, payload)
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(*channels)
        except Exception as e:
            print(f"Redis Pub/Sub listener error: {e}")


# Instantiation
if USE_REDIS:
    state_manager = RedisStateManager()
    # Initialize connection asynchronously on startup
else:
    state_manager = InMemoryStateManager()
