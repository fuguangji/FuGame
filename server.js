import WebSocket, { WebSocketServer } from "ws";
import admin from "firebase-admin";
import fs from "fs";

// 1️⃣ 初始化 Firebase Admin
const serviceAccount = JSON.parse(fs.readFileSync("./serviceAccount.json", "utf-8"));

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

// 2️⃣ 建立 WebSocket Server
const wss = new WebSocketServer({ port: 8080 });
console.log("WebSocket 伺服器啟動在 ws://localhost:8080");

wss.on("connection", async (ws, req) => {
  try {
    // 3️⃣ 從 URL 拿 ID Token
    const url = new URL(req.url, "https://dummy.com");
    const idToken = url.searchParams.get("token");
    if (!idToken) throw new Error("缺少 Token");

    // 4️⃣ 驗證 Firebase ID Token
    const decodedToken = await admin.auth().verifyIdToken(idToken);
    ws.userId = decodedToken.uid; // UID 綁定連線

    ws.send(JSON.stringify({ success: true, message: "登入成功", uid: ws.userId }));
    console.log(`使用者 ${ws.userId} 已連線`);

    // 5️⃣ 監聽訊息
    ws.on("message", (msg) => {
      try {
        const data = JSON.parse(msg);

        // 只允許 UID 自己修改自己的資料
        if (data.action === "updateProfile" && data.uid === ws.userId) {
          console.log(`使用者 ${ws.userId} 更新資料:`, data.payload);

          // TODO: 改成你資料庫的更新邏輯
          // updateDatabase(ws.userId, data.payload);

          ws.send(JSON.stringify({ success: true, message: "更新成功" }));
        } else {
          ws.send(JSON.stringify({ success: false, message: "非法操作" }));
        }
      } catch (err) {
        ws.send(JSON.stringify({ success: false, message: "訊息格式錯誤" }));
      }
    });

  } catch (err) {
    console.log("連線驗證失敗:", err.message);
    ws.close();
  }
});
