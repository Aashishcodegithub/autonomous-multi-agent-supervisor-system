from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# ==============================================================================
# Day 3: Tools & Agents
#
# Goal: Give the LLM "tools" (Python functions) it can call to interact with the
# outside world, perform calculations, fetch data, etc.
# ==============================================================================

# 1. Define tools using the @tool decorator
# The docstring is CRITICAL here, as it tells the LLM when and how to use the tool.
@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers together."""
    return a * b

@tool
def get_weather(location: str) -> str:
    """Get the current weather for a given location."""
    # This is a mock function, in reality you'd call a real weather API here
    if "tokyo" in location.lower():
        return "It's sunny and 25°C in Tokyo."
    elif "london" in location.lower():
        return "It's rainy and 15°C in London."
    return f"Weather data not available for {location}, but it's probably nice."

tools = [multiply, get_weather]

# 2. Initialize the LLM (Gemini 3.5 Flash supports tool calling)
llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")

# 3. Create the Agent using LangGraph
# LangGraph is the modern standard for building agents in the LangChain ecosystem.
agent_executor = create_react_agent(llm, tools)

# 4. Run the Agent!
if __name__ == "__main__":
    def print_stream(stream):
        for s in stream:
            message = s["messages"][-1]
            if isinstance(message, tuple):
                print(message)
            else:
                message.pretty_print()

    print("\n--- Test 1: Using the multiply tool ---")
    inputs = {"messages": [("user", "What is 15 multiplied by 7?")]}
    print_stream(agent_executor.stream(inputs, stream_mode="values"))
    
    print("\n--- Test 2: Using the weather tool ---")
    inputs = {"messages": [("user", "What is the weather like in Tokyo right now?")]}
    print_stream(agent_executor.stream(inputs, stream_mode="values"))

    print("\n--- Test 3: Normal conversation (no tools needed) ---")
    inputs = {"messages": [("user", "Hi! My name is Alice, and I am learning about Agents.")]}
    print_stream(agent_executor.stream(inputs, stream_mode="values"))