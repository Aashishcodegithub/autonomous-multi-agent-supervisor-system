from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# Tools
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

tools = [add, subtract, multiply, divide]

# Agent
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")
agent_executor = create_react_agent(llm, tools)

# Conversation history
messages = []

print("🧮 Calculator Agent ready! Type 'calculation done' to exit.\n")

while True:
    user_input = input("You: ")
    
    if user_input.lower() == "calculation done":
        print("Agent: Goodbye! All calculations complete.")
        break
    
    messages.append(("user", user_input))
    
    result = agent_executor.invoke({"messages": messages})
    
    response = result["messages"][-1].content
    
    # Handle list response
    if isinstance(response, list):
        for part in response:
            if isinstance(part, dict) and part.get("type") == "text":
                response = part["text"]
                break
    
    print(f"Agent: {response}\n")
    messages.append(("assistant", response))