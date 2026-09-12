#!/bin/bash
# M15 e2e: creates an ntfy and a Telegram agent pointed at tests/mock_webhook.py (port 8099), fires every
# event through notify_event and checks the fan-out honours subscriptions. Needs the app venv at
# ~/.venvs/the-den and a running backend on 8687 with AUTH_REQUIRED=false; DATABASE_URL must match it.
cd /mnt/c/projects/theden; V=~/.venvs/the-den/bin/python; D=~/the-den-test; export DATABASE_URL="sqlite:///$D/den.db" STATE_DIR=$D/state
pkill -f "mock_webhook"; sleep 1
setsid nohup $V -m uvicorn tests.mock_webhook:app --host 127.0.0.1 --port 8099 > /tmp/mockwh.log 2>&1 < /dev/null & sleep 3
B=http://127.0.0.1:8687/api/notifications
curl -s $B/agents | $V -c "import sys,json; [print('deleting', a['id']) for a in json.load(sys.stdin)]" 
for id in $(curl -s $B/agents | $V -c "import sys,json; print(' '.join(str(a['id']) for a in json.load(sys.stdin)))"); do curl -s -o /dev/null -X DELETE $B/agents/$id; done
curl -s -X POST $B/agents -H 'Content-Type: application/json' -d '{"name":"phone","kind":"ntfy","config":{"url":"http://127.0.0.1:8099","topic":"den","token":"secret123","priority":4},"events":[]}' > /dev/null
curl -s -X POST $B/agents -H 'Content-Type: application/json' -d '{"name":"tg","kind":"telegram","config":{"bot_token":"123:ABC","chat_id":"42","api_url":"http://127.0.0.1:8099"},"events":["imported","request_available"]}' > /dev/null
curl -s -X POST http://127.0.0.1:8099/reset > /dev/null
echo "--- agents (token blanked, has_token true?)"; curl -s $B/agents | $V -c "import sys,json; [print(' ', a['name'], a['config'], {k:v for k,v in a.items() if k.startswith('has_')}) for a in json.load(sys.stdin)]"
$V - <<'PY'
import asyncio, sys; sys.path.insert(0, ".")
from app.db import SessionLocal
from app.notifier import EVENTS, notify_event
async def main():
    db = SessionLocal()
    for ev in EVENTS:
        await notify_event(db, ev, f"msg for {ev}")
asyncio.run(main())
PY
curl -s http://127.0.0.1:8099/received | $V -c "
import sys,json; r=json.load(sys.stdin)
ntfy=[x for x in r if 'topic' in x]; tg=[x for x in r if 'telegram' in x]
print(len(ntfy),'ntfy posts (expect 9):', [x['tags'] for x in ntfy])
print('  sample:', ntfy[0])
print(len(tg),'telegram posts (expect 2):', [x['text'].split(chr(10))[0] for x in tg])
"
