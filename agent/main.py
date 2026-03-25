from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

# ---- state ----
class State(TypedDict):
    query: str
    tool_result: str
    answer: str
# ---- nodes ----

def decide(state: State):
    q = state["query"]
    if any(op in q for op in ["+", "-", "*", "/"]):
        return {"tool": "calculator"}
    return {"tool": "llm"}

def calculator(state: State):
    result = str(eval(state["query"]))
    return {"tool_result": result}

def generate(state: State):
    if "tool_result" in state:
        return {"answer": f"Result: {state['tool_result']}"}
    response = llm.invoke(state["query"])
    return {"answer": response.content}

# ---- graph ----
builder = StateGraph(State)

builder.add_node("decide", decide)
builder.add_node("calculator", calculator)
builder.add_node("generate", generate)

builder.set_entry_point("decide")

# conditional routing
def route(state: State):
    return state["tool"]

builder.add_conditional_edges(
    "decide",
    route,
    {
        "calculator": "calculator",
        "llm": "generate"
    }
)

builder.add_edge("calculator", "generate")
builder.add_edge("generate", END)

graph = builder.compile()

# ---- run ----
result = graph.invoke({"query": "25 * 4"})
print(result["answer"])