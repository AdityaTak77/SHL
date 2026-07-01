import sys
import os

sys.path.insert(0, os.path.abspath("."))
from app.state import extract_state, needs_clarification

messages = [
    {"role": "user", "content": "hi"},
    {"role": "assistant", "content": "To recommend the best tests..."},
    {"role": "user", "content": "python, fast api"}
]

state = extract_state(messages)
turn_count = state["turn_count"]

print(f"turn_count: {turn_count}")
print(f"role_categories: {state['role_categories']}")
print(f"technical_skills: {state['technical_skills']}")
print(f"seniority: {state['seniority']}")
print(f"needs_clarification: {needs_clarification(state, turn_count)}")
