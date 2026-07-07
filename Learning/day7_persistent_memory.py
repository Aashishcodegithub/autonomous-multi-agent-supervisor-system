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

# Load env variables
load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# Define a subclass to safely override invoke for rate-limiting
class RateLimitedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    def invoke(self, *args, **kwargs):
        # Enforce a 12-second delay between LLM calls to stay under the 5 RPM free tier limit
        time.sleep(12)
        for attempt in range(4):
            try:
                return super().invoke(*args, **kwargs)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg:
                    wait_time = 30 + (attempt * 10)
                    print(f"\n⚠️  [Rate Limit / 503] Hit on attempt {attempt + 1}. Waiting {wait_time}s before retrying...")
                    time.sleep(wait_time)
                else:
                    raise e
        return super().invoke(*args, **kwargs)

# Initialize the Gemini model
llm = RateLimitedChatGoogleGenerativeAI(model="gemini-2.5-flash")

# 1. Define Tools for the Math Worker
@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b

@tool
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        return "Error: Cannot divide by zero"
    return a / b

math_tools = [add, subtract, multiply, divide]
math_agent = create_react_agent(llm, math_tools)

# 2. Define the Agent State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str

# 3. Define the Supervisor Routing Schema
class RouteResponse(BaseModel):
    next: Literal["math_worker", "writer_worker", "FINISH"] = Field(
        description="The next agent to act, or FINISH if the user request is completely addressed."
    )
    reasoning: str = Field(description="Reasoning behind routing decision.")

structured_llm = llm.with_structured_output(RouteResponse)

# 4. Define the Nodes
def supervisor_node(state: AgentState):
    print("\n🕵️  [Supervisor] Deciding next action...")
    messages = state["messages"]
    
    system_prompt = (
        "You are the supervisor agent orchestrating a team of two workers:\n"
        "1. math_worker: specialized in math, calculations, and arithmetic tools.\n"
        "2. writer_worker: specialized in writing, summarizing, editing, and formatting.\n\n"
        "Based on the conversation history, choose who should act next or select 'FINISH' if the user's request has been fully addressed.\n"
        "If a worker has already provided the final result, you should select 'FINISH'."
    )
    
    prompt_messages = [SystemMessage(content=system_prompt)] + list(messages)
    decision = structured_llm.invoke(prompt_messages)
    print(f"🕵️  [Supervisor Decision] Next: {decision.next} | Reasoning: {decision.reasoning}")
    return {"next": decision.next}

def math_worker_node(state: AgentState):
    print("🧮 [Math Worker] Thinking/Calculating...")
    result = math_agent.invoke({"messages": state["messages"]})
    new_message = result["messages"][-1]
    new_message.content = f"[Math Worker Output] {new_message.content}"
    return {
        "messages": [new_message],
        "next": "supervisor"
    }

def writer_worker_node(state: AgentState):
    print("✍️  [Writer Worker] Generating response...")
    system_prompt = (
        "You are a professional writer worker. Your job is to format, summarize, or compose "
        "well-written text as requested by the user."
    )
    prompt_messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm.invoke(prompt_messages)
    
    new_message = AIMessage(content=f"[Writer Worker Output] {response.content}")
    return {
        "messages": [new_message],
        "next": "supervisor"
    }

# 5. Build the Graph with Checkpointer
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("math_worker", math_worker_node)
workflow.add_node("writer_worker", writer_worker_node)

workflow.add_edge(START, "supervisor")

def route_next(state: AgentState):
    return state["next"]

workflow.add_conditional_edges(
    "supervisor",
    route_next,
    {
        "math_worker": "math_worker",
        "writer_worker": "writer_worker",
        "FINISH": END
    }
)

workflow.add_edge("math_worker", "supervisor")
workflow.add_edge("writer_worker", "supervisor")

# Enable memory by compiling with a checkpointer
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# 6. Execute Programmatic Multi-Turn Demo
if __name__ == "__main__":
    print("🏗️  Building supervisor multi-agent graph with persistent memory...")
    
    # Define a thread configuration
    config = {"configurable": {"thread_id": "session-123"}}
    
    # Turn 1: Introduce ourselves
    turn1_query = "Hello, my name is Aashish."
    print(f"\n--- TURN 1: User says '{turn1_query}' ---")
    output_turn1 = app.invoke({"messages": [HumanMessage(content=turn1_query)], "next": "supervisor"}, config)
    print("\n--- TURN 1 CONVERSATION HISTORY ---")
    for msg in output_turn1["messages"]:
        print(f"[{type(msg).__name__}]: {msg.content}")
        
    # Turn 2: Ask about the name to verify memory
    turn2_query = "What is my name?"
    print(f"\n--- TURN 2: User says '{turn2_query}' ---")
    output_turn2 = app.invoke({"messages": [HumanMessage(content=turn2_query)], "next": "supervisor"}, config)
    print("\n--- TURN 2 CONVERSATION HISTORY ---")
    for msg in output_turn2["messages"]:
        print(f"[{type(msg).__name__}]: {msg.content}")

    # Turn 3: Ask to perform a calculation based on memory
    turn3_query = "Count the number of letters in my name and multiply it by 42."
    print(f"\n--- TURN 3: User says '{turn3_query}' ---")
    output_turn3 = app.invoke({"messages": [HumanMessage(content=turn3_query)], "next": "supervisor"}, config)
    print("\n--- TURN 3 CONVERSATION HISTORY ---")
    for msg in output_turn3["messages"]:
        print(f"[{type(msg).__name__}]: {msg.content}")
