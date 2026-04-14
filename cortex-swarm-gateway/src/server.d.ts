import express from "express";
export declare class CortexSwarmServer {
    private server;
    private transport;
    constructor();
    private setupHandlers;
    handleSseConnection(req: express.Request, res: express.Response): Promise<void>;
    handleMessage(req: express.Request, res: express.Response): Promise<void>;
}
//# sourceMappingURL=server.d.ts.map