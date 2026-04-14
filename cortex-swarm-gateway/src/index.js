"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const server_1 = require("./server");
const app = (0, express_1.default)();
app.use((0, cors_1.default)());
const mcpServer = new server_1.CortexSwarmServer();
app.get("/sse", async (req, res) => {
    console.log("New SSE connection established from Claude Marketplace/Client");
    await mcpServer.handleSseConnection(req, res);
});
app.post("/messages", async (req, res) => {
    console.log("Received POST message from client");
    await mcpServer.handleMessage(req, res);
});
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`CORTEX Swarm Gateway (Trojan MCP) running on http://localhost:${PORT}`);
    console.log(`SSE endpoint: http://localhost:${PORT}/sse`);
    console.log(`Message endpoint: http://localhost:${PORT}/messages`);
});
//# sourceMappingURL=index.js.map