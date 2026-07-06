import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import database

print("Testing database module...")
print("Current user email:", database.get_current_user_email())

print("Testing session creation...")
session_id = database.create_session("Test Scoped Chat")
print(f"Created session ID: {session_id}")

print("Testing fetching sessions...")
sessions = database.get_all_sessions()
print(f"Fetched {len(sessions)} sessions.")
found_test_sess = False
for s in sessions:
    print(f"Session ID={s['id']}, Title={s['title']}, Email={s.get('user_email')}")
    if s['id'] == session_id:
        found_test_sess = True

if not found_test_sess:
    print("WARNING: Created session not found in the fetched list!")
else:
    print("SUCCESS: Session created and fetched successfully.")

print("Testing message creation...")
msg_id = database.add_message(session_id, 'user', 'Hello ASTROGEN', msg_type='text')
print(f"Created message ID: {msg_id}")

# Let's save a duplicate image base64 message manually to test deduplication
b64_content = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
msg_id_img1 = database.add_message(session_id, 'assistant', b64_content, msg_type='image')
msg_id_img2 = database.add_message(session_id, 'assistant', b64_content, msg_type='image')

print("Testing sync check (dry run / check limits)...")
database.sync_local_to_cloud()

print("Testing message retrieval & resolution of duplicate image base64...")
messages = database.get_session_messages(session_id)
print(f"Retrieved {len(messages)} messages.")
for m in messages:
    print(f"Message ID={m['id']}, Role={m['role']}, Type={m['msg_type']}, Content={m['content'][:60]}...")

print("Cleaning up test session...")
database.delete_session(session_id)
print("Finished testing!")
