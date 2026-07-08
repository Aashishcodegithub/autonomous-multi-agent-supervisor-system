# day8.py
from typing import TypedDict, Annotated, Sequence, Literal
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# Rate-limiting wrapper from Day 7
class RateLimitedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    def invoke(self, *args, **kwargs):
        time.sleep(2)  # Reduced slightly for development, adjust as needed
        for attempt in range(4):
            try:
                return super().invoke(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print(f"\n⚠️ Rate limit hit. Waiting 15s...")
                    time.sleep(15)
                else:
                    raise e
        return super().invoke(*args, **kwargs)

llm = RateLimitedChatGoogleGenerativeAI(model="gemini-2.5-flash")

# --- 1. Tools & Sub-Agents ---
@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

math_agent = create_react_agent(llm, [multiply])

# --- 2. State & Router Schemas ---
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str

class RouteResponse(BaseModel):
    next: Literal["math_worker", "writer_worker", "FINISH"] = Field(
        description="The next agent to act, or FINISH."
    )
    reasoning: str = Field(description="Reasoning behind routing decision.")

structured_llm = llm.with_structured_output(RouteResponse)

# --- 3. Graph Nodes ---
def supervisor_node(state: AgentState):
    print("\n🕵️  [Supervisor] Deciding next action...")
    system_prompt = (
        "You are the supervisor agent orchestrating a team of workers:\n"
        "1. math_worker: for math and calculations.\n"
        "2. writer_worker: for text formatting, essays, or summaries.\n"
        "Choose who should act next or select 'FINISH' if the request is done."
    )
    prompt_messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    decision = structured_llm.invoke(prompt_messages)
    print(f"🕵️  [Supervisor Decision] Next: {decision.next} | Reasoning: {decision.reasoning}")
    return {"next": decision.next}

def math_worker_node(state: AgentState):
    print("🧮 [Math Worker] Thinking/Calculating...")
    result = math_agent.invoke({"messages": state["messages"]})
    new_message = result["messages"][-1]
    new_message.content = f"[Math Worker Output] {new_message.content}"
    return {"messages": [new_message], "next": "supervisor"}

def writer_worker_node(state: AgentState):
    print("✍️  [Writer Worker] Processing text...")
    system_prompt = "You are a professional writer worker. Provide clean, well-formatted text answers."
    prompt_messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm.invoke(prompt_messages)
    return {"messages": [AIMessage(content=f"[Writer Worker Output] {response.content}")], "next": "supervisor"}

# --- 4. Graph Construction ---
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("math_worker", math_worker_node)
workflow.add_node("writer_worker", writer_worker_node)

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges("supervisor", lambda state: state["next"], {
    "math_worker": "math_worker",
    "writer_worker": "writer_worker",
    "FINISH": END
})
workflow.add_edge("math_worker", "supervisor")
workflow.add_edge("writer_worker", "supervisor")

checkpointer = MemorySaver()

# 🔥 NEW FOR DAY 8: Compile with an interrupt checkpoint before executing the math worker!
app = workflow.compile(checkpointer=checkpointer, interrupt_before=["math_worker"])

# --- 5. Execution Demo ---
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "day8-session"}}
    
    # User requests a math action
    query = "Multiply 1234 by 56"
    print(f"🚀 User: {query}")
    
    # Run the graph until it hits a breakpoint or finishes
    for event in app.stream({"messages": [HumanMessage(content=query)]}, config, stream_mode="values"):
        pass 
    
    # Check if the graph is currently paused at a breakpoint
    snapshot = app.get_state(config)
    if snapshot.next and "math_worker" in snapshot.next:
        print("\n🛑 [HITL BREAKPOINT] Graph paused safely right before 'math_worker' executes.")
        print(f"Supervisor wants to hand off control to: {snapshot.next}")
        
        # Human Interaction Loop
        user_choice = input("Proceed? (y = Approve / n = Abort / or type a correction message): ").strip()
        
        if user_choice.lower() == 'y':
            print("✅ Human Approved! Resuming execution...")
            # Pass None to resume exactly where it was intercepted
            for event in app.stream(None, config, stream_mode="values"):
                pass
        else:
            print("❌ Execution halted or overridden by human.")
            
    # Final Output Check
    final_snapshot = app.get_state(config)
    print("\n--- FINAL STATE MESSAGES ---")
    for msg in final_snapshot.values["messages"]:
        print(f"[{type(msg).__name__}]: {msg.content}")