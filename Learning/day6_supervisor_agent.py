from typing import TypedDict, Annotated, Sequence, Literal
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from pathlib import Path
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# Helper function to extract clean text content from LangChain messages
def get_clean_content(message_content) -> str:
    if isinstance(message_content, list):
        for part in message_content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    return part.get("text", "")
            elif hasattr(part, "text"):
                return part.text
        return str(message_content)
    return str(message_content)

# Helper function to remove large signatures/metadata tokens from messages
def clean_messages(messages):
    cleaned = []
    for msg in messages:
        content = get_clean_content(msg.content)
        # Strip out [Math Worker Output] prefixes if they accumulate, keep clean text
        if isinstance(msg, HumanMessage):
            cleaned.append(HumanMessage(content=content))
        elif isinstance(msg, AIMessage):
            cleaned.append(AIMessage(content=content))
        elif isinstance(msg, SystemMessage):
            cleaned.append(SystemMessage(content=content))
    return cleaned

# Subclass for rate-limiting
class RateLimitedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    def invoke(self, *args, **kwargs):
        # Enforce a 6-second delay between calls (safe under 15 RPM for 2.0/3.5 models)
        time.sleep(6)
        # Clean input messages if passed
        if args and isinstance(args[0], list):
            args = (clean_messages(args[0]),) + args[1:]
        for attempt in range(4):
            try:
                return super().invoke(*args, **kwargs)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg:
                    wait_time = 15 + (attempt * 10)
                    print(f"\n⚠️  [Rate Limit] Waiting {wait_time}s before retrying...")
                    time.sleep(wait_time)
                else:
                    raise e
        return super().invoke(*args, **kwargs)

# Initialize the Gemini model
llm = RateLimitedChatGoogleGenerativeAI(model="gemini-2.5-flash")

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
    print("\n🕵️  [Supervisor] Deciding starting action...")
    messages = clean_messages(state["messages"])
    
    system_prompt = (
        "You are the supervisor agent orchestrating a team of two workers:\n"
        "1. math_worker: specialized in math, calculations, and arithmetic.\n"
        "2. writer_worker: specialized in writing, summarizing, and formatting.\n\n"
        "Based on the user request, decide who should start. If the request requires math, route to math_worker. "
        "If it is purely writing or formatting, route to writer_worker. If already finished, choose FINISH."
    )
    
    prompt_messages = [SystemMessage(content=system_prompt)] + messages
    decision = structured_llm.invoke(prompt_messages)
    print(f"🕵️  [Supervisor Decision] Next: {decision.next} | Reasoning: {decision.reasoning}")
    return {"next": decision.next}

def math_worker_node(state: AgentState):
    print("🧮 [Math Worker] Calculating...")
    last_msg = get_clean_content(state["messages"][-1].content)
    
    prompt = (
        f"Solve the mathematical calculations in the following request. "
        f"Provide the step-by-step arithmetic operations and the final numeric result clearly.\n"
        f"Request: {last_msg}"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    clean_text = get_clean_content(response.content)
    print(f"🧮 [Math Worker Output]: {clean_text}")
    
    return {
        "messages": [AIMessage(content=f"Math Result: {clean_text}")],
        "next": "writer_worker"  # Chain directly to the writer worker to compile the final answer
    }

def writer_worker_node(state: AgentState):
    print("✍️  [Writer Worker] Formatting response and adding context...")
    messages = clean_messages(state["messages"])
    
    # Compile history as strings
    history_str = "\n".join([f"{type(m).__name__}: {m.content}" for m in messages])
    
    prompt = (
        f"Based on the following conversation and calculation results, formulate the final output. "
        f"Make sure to provide the requested fun fact or summary in a polite, creative, and professional tone.\n\n"
        f"History:\n{history_str}"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    clean_text = get_clean_content(response.content)
    print(f"✍️  [Writer Worker Output]: {clean_text}")
    
    return {
        "messages": [AIMessage(content=clean_text)],
        "next": "FINISH"
    }

# 5. Build the Graph
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

# Math worker routes directly to writer worker
workflow.add_edge("math_worker", "writer_worker")
# Writer worker routes directly to END
workflow.add_edge("writer_worker", END)

app = workflow.compile()

# 6. Execute
if __name__ == "__main__":
    print("🏗️  Building supervisor multi-agent graph...")
    query = "Calculate (152 * 43) / 12 and write a brief one-sentence fun fact about the result."
    print(f"🚀 Running with query: '{query}'\n")
    
    initial_state = {"messages": [HumanMessage(content=query)], "next": "supervisor"}
    final_output = app.invoke(initial_state)
    
    print("\n--- FINAL CONVERSATION LOG ---")
    for msg in final_output["messages"]:
        print(f"\n[{type(msg).__name__}]:\n{get_clean_content(msg.content)}")
