from datetime import datetime
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage,SystemMessage, RemoveMessage
from langgraph.graph import StateGraph,START,END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Annotated
import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from app.RAG.operations.retrival_pipeline import get_retrival_pipeleine
load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")


def merge_dict(old: dict | None, new: dict | None) -> dict:
    if old is None:
        return new
    if new is None:
        return old
    return {**old, **new}

class RemainderData(TypedDict):
    operation: Annotated[str, ..., "One of 'view','create', 'update', 'delete' — what the user wants done with the reminder"]
    course_name: Annotated[str, ..., "Name of the course for which remainder has to be created, updated, or deleted"]
    remainder_time: Optional[datetime]

class State(TypedDict):
    summary:str
    messages: Annotated[list, add_messages]
    intent: Annotated[str, ..., "Should indicate the intent of user query only from [RAG,remainder,general]"]
    refined_query: Annotated[str, ..., "Refine the query incase the intent is to query RAG without changing the context"]
    remainder_data: Annotated[RemainderData, merge_dict]
    tool_response: str

class IntentRespone(TypedDict):
    """Request data format"""
    intent: Annotated[str, ..., "Should indicate the intent of user query only from [RAG,remainder,general], anything related to academics comes under RAG"]
    refined_query: Annotated[str, ..., "Refine the query incase the intent is to query RAG without changing the context"]
    remainder_data: RemainderData


def get_chat_bot(llm_name:str):
    llm = init_chat_model(model=llm_name)
    return llm

def remainder_tool(state:State):
    """Creates an academic reminder (quiz, Digital Assignment, Project review, class reminder)
    using course_name and remainder_time already present in state.

    Returns:
        dict: Updates 'tool_response' with a confirmation message.
    """
    return {'tool_response':"Remainder created successfully"}

def RAG_tool(state:State):
    """Answers queries related to VIT rules and regulations using the retrieval pipeline,
    driven by 'refined_query' already present in state.

    Returns:
        dict: Updates 'tool_response' with the retrieved answer.
    """
    retriver = get_retrival_pipeleine()
    response = retriver.process_query(state['refined_query'], top_k=10)
    return {'tool_response':response.get("answer")[0].get("text")}


llm = get_chat_bot("groq:openai/gpt-oss-20b") 
structured_agent = llm.with_structured_output(IntentRespone,method='json_mode')

def summarize_conversation(state:State):
    if(len(state['messages'])<20):
        return {}
    summary = state.get('summary','')
    prompt = (
        f"Extend this summary with the new messages: {summary}" if summary
        else "Summarize the conversation so far."
    )
    response = llm.invoke(state["messages"][:-6] + [HumanMessage(content=prompt)])
    delete_messages = [RemoveMessage(id=m.id) for m in state['messages'][:-6]]
    return {"summary":response.content,"messages":delete_messages}

def classify_intent(state: State):
    system_prompt = SystemMessage(content=(
        "You are an intent classifier, assume every query is related to VIT. Respond only with a JSON object with these keys: "
        "intent (one of 'RAG', 'remainder', 'general'), refined_query (string), "
        "remainder_data (an object with: operation, course_name, remainder_time). "
        "For remainder_data.operation: use 'create' if the user is asking to set a new reminder, "
        "'view' if they're asking to see or list their existing reminders, "
        "'update' if they're asking to change the time/details of an existing reminder, "
        "'delete' if they're asking to cancel or remove a reminder. "
        "remainder_time should be an ISO datetime string, or null if not mentioned. "
        "If any doubt is related to academics(VIT)/hostels/mess/examinations then classify it as RAG."
    ))
    result = structured_agent.invoke([system_prompt] +[f"Earlier conversation summary:{state['summary']}"]+state['messages'])
    print(result)
    data ={
        "intent": result["intent"],
        "refined_query": result["refined_query"],
        "remainder_data": result["remainder_data"],
    }
    return data

def route_by_intent(state:State):
    if(state['intent'] == 'RAG'):
        return "RAG"
    elif state['intent']=='remainder':
        return "remainder"
    return "general"

def chatbot(state:State):
    if state['intent']!='general' and state['tool_response']!='Not Found in Documents':
        return {"messages":[AIMessage(content=state['tool_response'])]}
    system_prompt = SystemMessage(content=(
        "You are a helpful assistant for VIT students. Assume every HumanMessage query is related to VIT. "
        "Answer as accurately and helpfully as you can based only on previous context if they contains the answer else using your own knowledge."
    ))
    return {"messages":[llm.invoke([system_prompt]+[f"Earlier conversation summary:{state['summary']}"]+state['messages'])],"tool_response": ""}



graph_builder = StateGraph(State)

graph_builder.add_node("intent_classifier",classify_intent)
graph_builder.add_node("RAG",RAG_tool)
graph_builder.add_node("remainder",remainder_tool)
graph_builder.add_node("chatbot",chatbot)
graph_builder.add_node("summarizer",summarize_conversation)

graph_builder.add_edge(START,"summarizer")
graph_builder.add_edge("summarizer","intent_classifier")
graph_builder.add_conditional_edges(
    "intent_classifier",
    route_by_intent,
    {
        "RAG":"RAG",
        "remainder":"remainder",
        "general":"chatbot"
    }
)
graph_builder.add_edge("RAG","chatbot")
graph_builder.add_edge("remainder","chatbot")
graph_builder.add_edge("chatbot",END)


graph = None

def invoke_graph(query:str,user_id,chat_id):
    config = {
        "configurable":{
            "thread_id":f'{user_id}_{chat_id}'
        }
    }
    response = graph.invoke({"messages":query},config=config)
    return response['messages'][-1].content