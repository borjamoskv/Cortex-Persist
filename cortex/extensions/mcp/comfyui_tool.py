# [C5-REAL] Exergy-Maximized
import json
import uuid

# CORTEX-Persist Visual Engine (ComfyUI)
# MCP Tool Bridge


def run_comfyui_workflow(workflow_json: str) -> str:
    """
    Executes a deterministic C5-REAL ComfyUI JSON workflow.

    Args:
        workflow_json (str): The stringified JSON DAG to execute on the local ComfyUI instance.

    Returns:
        str: A JSON string containing the paths of the generated assets or an error trace.
    """
    import urllib.error
    import urllib.parse
    import urllib.request

    SERVER_ADDRESS = "127.0.0.1:8188"
    CLIENT_ID = str(uuid.uuid4())

    try:
        graph = json.loads(workflow_json)
    except json.JSONDecodeError:
        return json.dumps({"status": "error", "message": "Invalid JSON workflow provided."})

    def queue_prompt(prompt):
        p = {"prompt": prompt, "client_id": CLIENT_ID}
        data = json.dumps(p).encode("utf-8")
        req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    try:
        prompt_res = queue_prompt(graph)
        prompt_id = prompt_res["prompt_id"]
    except urllib.error.URLError:
        return json.dumps(
            {
                "status": "error",
                "message": "ComfyUI node unreachable. Ensure 127.0.0.1:8188 is active.",
            }
        )

    # Note: For MCP synchrony, we don't open the WebSocket to block, we just queue it.
    # In a full CORTEX extension, we'd spawn a background Thread/Async task.
    # For now, we return the job ID.
    return json.dumps(
        {
            "status": "success",
            "message": "DAG injected into Visual Engine.",
            "prompt_id": prompt_id,
            "history_endpoint": f"http://{SERVER_ADDRESS}/history/{prompt_id}",
        }
    )
