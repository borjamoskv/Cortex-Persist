import express from "express";
import cors from "cors";
import { CortexSwarmServer } from "./server.js";

const app = express();
const gatewayToken = process.env.CORTEX_SWARM_GATEWAY_TOKEN;
const allowedOrigins = process.env.CORTEX_SWARM_GATEWAY_ORIGIN?.split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);
app.use(
  cors({
    origin: allowedOrigins && allowedOrigins.length > 0 ? allowedOrigins : false,
  })
);
app.use(express.json());
app.use((req, res, next) => {
  if (!gatewayToken) {
    next();
    return;
  }

  if (req.header("x-cortex-gateway-token") !== gatewayToken) {
    res.status(401).json({ error: "Unauthorized" });
    return;
  }

  next();
});

const mcpServer = new CortexSwarmServer();

app.get("/sse", async (req, res) => {
  console.log("New SSE connection established from Claude Marketplace/Client");
  await mcpServer.handleSseConnection(req, res);
});

app.post("/messages", async (req, res) => {
  console.log("Received POST message from client");
  await mcpServer.handleMessage(req, res);
});

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || "127.0.0.1";
app.listen(PORT, HOST, () => {
  console.log(`CORTEX Swarm Gateway running on http://${HOST}:${PORT}`);
  console.log(`SSE endpoint: http://${HOST}:${PORT}/sse`);
  console.log(`Message endpoint: http://${HOST}:${PORT}/messages`);
});
