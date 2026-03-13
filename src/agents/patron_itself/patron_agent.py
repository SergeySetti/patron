from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()


def get_weather(city: str) -> str:
    """Get weather for a given city"""
    return f"It's always sunny in {city}!"


model = ChatGoogleGenerativeAI(model="gemini-3.1-pro-preview")

agent = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)
