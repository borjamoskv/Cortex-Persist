import os
import shutil

ROOT = "cortex"

# 1. Mover carpetas
src_agent = os.path.join(ROOT, "extensions", "agent")
dst_agent = os.path.join(ROOT, "extensions", "agents")

if os.path.exists(src_agent):
    if not os.path.exists(dst_agent):
        os.makedirs(dst_agent)
    for item in os.listdir(src_agent):
        s = os.path.join(src_agent, item)
        d = os.path.join(dst_agent, item)
        if not os.path.exists(d):
            shutil.move(s, d)
        elif os.path.isdir(s):
            for sub_item in os.listdir(s):
                shutil.move(os.path.join(s, sub_item), os.path.join(d, sub_item))
    shutil.rmtree(src_agent)

src_swarm = os.path.join(ROOT, "engine", "swarm")
dst_swarm = os.path.join(ROOT, "swarm")

if os.path.exists(src_swarm):
    if not os.path.exists(dst_swarm):
        os.makedirs(dst_swarm)
    for item in os.listdir(src_swarm):
        s = os.path.join(src_swarm, item)
        d = os.path.join(dst_swarm, item)
        if not os.path.exists(d):
            shutil.move(s, d)
        elif os.path.isdir(s):
            for sub_item in os.listdir(s):
                shutil.move(os.path.join(s, sub_item), os.path.join(d, sub_item))
    shutil.rmtree(src_swarm)

# 2. Refactor ATOMICO
def atomic_replace(content):
    # Solamente hacemos matches seguros:
    c = content.replace("cortex.extensions.agent.", "cortex.extensions.agents.")
    c = c.replace("cortex.extensions.agent ", "cortex.extensions.agents ")
    c = c.replace("cortex.extensions.agent\\n", "cortex.extensions.agents\\n")
    c = c.replace("cortex.extensions.agent\\'", "cortex.extensions.agents\\'")
    c = c.replace("cortex.extensions.agent\\\"", "cortex.extensions.agents\\\"")
    
    c = c.replace("cortex.engine.swarm.", "cortex.swarm.")
    c = c.replace("cortex.engine.swarm ", "cortex.swarm ")
    c = c.replace("cortex.engine.swarm\\n", "cortex.swarm\\n")
    c = c.replace("cortex.engine.swarm\\'", "cortex.swarm\\'")
    c = c.replace("cortex.engine.swarm\\\"", "cortex.swarm\\\"")
    return c

for root, _, files in os.walk(ROOT):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                continue
            
            new_content = atomic_replace(content)
            if new_content != content:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)

print("✅ Migración P0 Completada de forma segura")
