import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

load_dotenv()

@tool
def get_weather(city: str) -> str:
    """Get weather for a given city.
    
    Args:
        city: The city to get the weather for.
    """
    return f"It's always sunny in {city}!"

def create_agent():
    """Creates and returns a LangChain agent executor."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    tools = [get_weather]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant named Patron."),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

# Exported agent executor instance
agent = create_agent()
