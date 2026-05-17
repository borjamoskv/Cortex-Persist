import sqlite3
import os
import uuid
from datetime import datetime

db_path = "/Users/borjafernandezangulo/.9router/db/data.sqlite"
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    print("Error: OPENAI_API_KEY not found in environment")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

id = str(uuid.uuid4())
provider = "openai"
auth_type = "apikey"
name = "OpenAI Default"
email = ""
priority = 1
is_active = 1
data_json = f'{{"apiKey":"{api_key}", "testStatus":"active"}}'
now = datetime.now().isoformat() + "Z"

try:
    cursor.execute(
        """
        INSERT INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (id, provider, auth_type, name, email, priority, is_active, data_json, now, now),
    )
    conn.commit()
    print(f"Successfully added OpenAI provider with ID: {id}")
except Exception as e:
    print(f"Error inserting into DB: {e}")
finally:
    conn.close()
