#!/usr/bin/env python3
"""
MOSKV-1 / CORTEX-Persist
C5-REAL ComfyUI Dispatcher

Este script actúa como el puente determinista entre Jules-Secretario y el
motor de compilación visual (ComfyUI). En lugar de usar prompts estocásticos,
enviamos el pipeline completo (Graph JSON) para forzar VRAM tensors.
"""

import json
import sys
import urllib.parse
import urllib.request
import uuid

import websocket

# Configuración del nodo ComfyUI
SERVER_ADDRESS = "127.0.0.1:8188"
CLIENT_ID = str(uuid.uuid4())

# JSON Payload Base (DAG Determinista)
# Este es un flujo de prueba C5-REAL estándar: Checkpoint -> Empty Latent -> KSampler -> VAE Decode -> Save Image
# En producción, Jules inyecta ControlNet, DepthMaps, y loras de 'Industrial Noir 2026'.
PROMPT_GRAPH = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 18273645,
            "steps": 25,
            "cfg": 7.0,
            "sampler_name": "euler_ancestral",
            "scheduler": "karras",
            "denoise": 1,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "v1-5-pruned-emaonly.ckpt"  # Replace with actual CORTEX model
        },
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {"batch_size": 1, "width": 1024, "height": 512},
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "Cyberpunk terminal interface, dark industrial noir, #0A0A0A base, #2B3BE5 glowing highlights, highly detailed, raw structural aesthetic",
            "clip": ["4", 1],
        },
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "text, watermark, ugly, soft, noisy, low resolution, colorful, bright",
            "clip": ["4", 1],
        },
    },
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "cortex_v1_", "images": ["8", 0]},
    },
}


def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": CLIENT_ID}
    data = json.dumps(p).encode("utf-8")
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/view?{url_values}")
    return urllib.request.urlopen(req).read()


def get_history(prompt_id):
    req = urllib.request.Request(f"http://{SERVER_ADDRESS}/history/{prompt_id}")
    return json.loads(urllib.request.urlopen(req).read())


def run_c5_real_pipeline():
    ws = websocket.WebSocket()

    try:
        ws.connect(f"ws://{SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")
    except Exception:
        sys.exit(1)

    prompt_res = queue_prompt(PROMPT_GRAPH)
    prompt_id = prompt_res["prompt_id"]

    # Listen to WebSocket
    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message["type"] == "executing":
                data = message["data"]
                if data["node"] is None and data["prompt_id"] == prompt_id:
                    break  # Execution is done
            elif message["type"] == "progress":
                data = message["data"]
        else:
            continue

    # Check history for outputs
    history = get_history(prompt_id)[prompt_id]
    for node_id in history["outputs"]:
        node_output = history["outputs"][node_id]
        if "images" in node_output:
            for image in node_output["images"]:
                img_data = get_image(image["filename"], image["subfolder"], image["type"])
                output_path = f"/Users/borjafernandezangulo/Music/VISUALES/{image['filename']}"
                with open(output_path, "wb") as f:
                    f.write(img_data)


if __name__ == "__main__":
    run_c5_real_pipeline()
