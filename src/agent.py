from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, MessageGraph

def get_agent():
    """
    This function creates and returns a LangGraph agent.
    """
    graph = MessageGraph()

    graph.add_node("oracle", lambda state: HumanMessage(content="Hello, world!"))
    graph.add_edge("oracle", END)

    graph.set_entry_point("oracle")

    return graph.compile()

if __name__ == "__main__":
    agent = get_agent()
    for s in agent.stream([]):
        print(s)
