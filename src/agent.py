from langchain.chat_models import init_chat_model

# def get_agent():
"""
This function creates and returns a LangGraph agent.
"""
llm = init_chat_model("google_genai:gemini-2.0-flash")
response = llm.invoke("Hello, world!")
print(response.content)