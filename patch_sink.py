
with open("scripts/moltbook_entropy_sink.py") as f:
    code = f.read()

code = code.replace(
    'dms = client._request("GET", "/agents/dm/requests")',
    'dms = await client._request("GET", "/agents/dm/requests")'
)

code = code.replace(
    'notifs = client._request("GET", "/notifications")',
    'notifs = await client._request("GET", "/notifications")'
)

code = code.replace(
    'client.mark_notifications_read(pid)',
    'await client.mark_notifications_read(pid)'
)

with open("scripts/moltbook_entropy_sink.py", "w") as f:
    f.write(code)

print("Patch applied.")
