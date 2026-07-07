from typing import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# 1. Define the State
# This TypedDict defines the structure of the data passed between nodes
class GraphState(TypedDict):
    topic: str
    draft: str
    review: str

# 2. Define the Nodes
# Each node is a function that takes the current state and returns a state update

def drafter_node(state: GraphState):
    print("✍️  [Drafter] Writing a short draft about:", state["topic"])
    prompt = f"Write a very short (2-3 sentences) informative draft about: {state['topic']}"
    response = llm.invoke(prompt)
    
    # Return a dictionary with just the keys we want to update
    return {"draft": response.content}

def reviewer_node(state: GraphState):
    print("🕵️  [Reviewer] Reviewing the draft...")
    draft = state.get("draft", "")
    prompt = f"Review this draft and provide one sentence of constructive feedback:\n\n{draft}"
    response = llm.invoke(prompt)
    
    return {"review": response.content}

# 3. Build the Graph
print("🏗️  Building the Graph...")
workflow = StateGraph(GraphState)

# Add nodes to the graph
workflow.add_node("drafter", drafter_node)
workflow.add_node("reviewer", reviewer_node)

# 4. Define the Edges
# START -> drafter -> reviewer -> END
workflow.add_edge(START, "drafter")
workflow.add_edge("drafter", "reviewer")
workflow.add_edge("reviewer", END)

# Compile the workflow into a runnable app
app = workflow.compile()

# 5. Run it!
print("🚀 Running the Graph!\n")
final_state = app.invoke({"topic": "The importance of state management in AI agents"})

print("\n--- FINAL OUTPUT ---")
print(f"Topic: {final_state['topic']}\n")
print(f"Draft:\n{final_state['draft']}\n")
print(f"Review:\n{final_state['review']}")
