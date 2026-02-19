from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------- Firebase ----------------
cred = credentials.Certificate("admin.json")  # 把 admin.json 放在 repo
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- FastAPI ----------------
app = FastAPI()

# 允許 TurboWarp 前端連線
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- WebSocket ----------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# ---------------- 世界狀態 ----------------
world = {
    "players": {},   # uid: {"gold":0, "pos":[0,0]}
}

# ---------------- WebSocket 路由 ----------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            uid = msg.get("uid")
            if not uid:
                continue

            # 初始化玩家
            if uid not in world["players"]:
                world["players"][uid] = {"gold":0, "pos":[0,0]}

            # 處理指令
            if msg.get("action") == "move":
                dx = msg.get("dx",0)
                dy = msg.get("dy",0)
                world["players"][uid]["pos"][0] += dx
                world["players"][uid]["pos"][1] += dy
            elif msg.get("action") == "add_gold":
                delta = msg.get("delta",0)
                world["players"][uid]["gold"] += delta

            # 廣播更新給所有玩家
            await manager.broadcast({"type":"update","world":world})

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ---------------- 定期快照到 Firebase ----------------
async def snapshot_loop():
    while True:
        for uid, pdata in world["players"].items():
            db.collection("players").document(uid).set(pdata)
        await asyncio.sleep(5)  # 每 5 秒快照一次

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(snapshot_loop())
