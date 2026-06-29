import logging

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kapso", tags=["kapso", "whatsapp"])

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Kapso / Meta Webhook Verification endpoint.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    # TODO: Fetch expected token from Cortex keyring
    expected_token = "CORTEX_KAPSO_VERIFY_TOKEN" 

    if mode and token:
        if mode == "subscribe" and token == expected_token:
            logger.info("Kapso Webhook verified.")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Forbidden")
    raise HTTPException(status_code=400, detail="Bad Request")


@router.post("/webhook")
async def receive_webhook(request: Request):
    """
    Receive incoming messages and status updates from Kapso.
    """
    try:
        payload = await request.json()
        logger.info(f"Received Kapso Webhook: {payload}")
        
        # Enforce CORTEX-TAINT and route to Sovereign Swarm or event bus
        # TBD based on specific use case
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error processing Kapso Webhook: {e}")
        # Return 200 anyway so Kapso doesn't retry unnecessarily for parsing errors
        return {"status": "error"}
