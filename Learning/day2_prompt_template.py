from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")

# Prompt template with variables
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant that explains technical concepts in a simple way."),
    ("human", "Explain {concept} in 2 sentences.")
])

chain = prompt | llm

response = chain.invoke({"concept": "LangGraph"})
# Cleanly print the output, extracting the text from thinking model metadata if present
if isinstance(response.content, list):
    for part in response.content:
        if part.get("type") == "text":
            print(part["text"])
else:
    print(response.content)