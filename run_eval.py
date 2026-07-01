import glob
import json
import os
import re
from typing import List, Dict

from dotenv import load_dotenv
load_dotenv(r"d:\SHL\.env")

from app.agent import run_agent

def parse_trace(filepath: str) -> Dict:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by turns
    turns_raw = re.split(r'### Turn \d+', content)[1:]
    
    conversation = []
    expected_items = set()
    
    for turn in turns_raw:
        # Extract user message
        user_match = re.search(r'\*\*User\*\*\s*>\s*(.*?)(?=\*\*Agent\*\*|$)', turn, re.DOTALL)
        if user_match:
            user_msg = user_match.group(1).strip()
            conversation.append({"role": "user", "content": user_msg})
            
        # Extract expected items from the agent's table if this is the final turn
        table_rows = re.findall(r'\|\s*\d+\s*\|\s*([^|]+?)\s*\|', turn)
        for row in table_rows:
            expected_items.add(row.strip().lower())
            
    return {
        "file": os.path.basename(filepath),
        "messages": conversation,
        "expected_items": expected_items
    }

def run_evaluation():
    traces = glob.glob(r"d:\SHL\sample_conversations\GenAI_SampleConversations\*.md")
    
    total_recall = 0.0
    
    for trace_path in traces:
        trace_data = parse_trace(trace_path)
        messages = trace_data["messages"]
        expected = trace_data["expected_items"]
        
        if not expected:
            print(f"Skipping {trace_data['file']} (No expected items found)")
            continue
            
        # Build history iteratively to simulate the conversation
        history = []
        final_recommendations = []
        
        for msg in messages:
            history.append(msg)
            # Call agent
            import time
            time.sleep(4)  # Prevent hitting 15 RPM Free Tier limit
            try:
                reply, recs, eoc = run_agent(history)
            except Exception as e:
                print(f"Agent error (rate limit?): {e}")
                continue
            
            # Agent reply
            history.append({"role": "assistant", "content": reply})
            
            # Update recommendations
            if recs:
                final_recommendations = recs
                
        # Calculate Recall
        retrieved_names = [r["name"].lower() for r in final_recommendations]
        hits = sum(1 for e in expected if any(e in r for r in retrieved_names))
        
        recall = hits / len(expected) if expected else 0.0
        total_recall += recall
        
        print(f"Trace: {trace_data['file']}")
        print(f"  Expected: {len(expected)}")
        print(f"  Retrieved: {len(final_recommendations)}")
        print(f"  Hits: {hits}")
        print(f"  Recall: {recall:.2f}\n")
        
    avg_recall = total_recall / len(traces)
    print(f"Average Recall across {len(traces)} traces: {avg_recall:.2f}")

if __name__ == "__main__":
    run_evaluation()
