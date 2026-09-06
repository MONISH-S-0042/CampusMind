from langgraph.types import Command
from langgraph.graph import StateGraph,START,END
from dotenv import load_dotenv
from app.services.langgraph_model import State
from app.services.remainder.create_remainder import check_course, check_extra, check_time, confirm_remainder, ask_correction, create_remainder
from app.services.core_nodes.core_nodes import RAG_tool, chatbot, classify_intent, remainder_end, route_by_intent, summarize_conversation,remainder_operation
from app.services.remainder.view_remainder import get_remainders
load_dotenv()

graph_builder = StateGraph(State)

graph_builder.add_node("intent_classifier",classify_intent)
graph_builder.add_node("RAG",RAG_tool)
graph_builder.add_node("chatbot",chatbot)
graph_builder.add_node("summarizer",summarize_conversation)

graph_builder.add_node("remainder_start",remainder_operation)
graph_builder.add_node("remainder_end",remainder_end)

#View Remainder
graph_builder.add_node("view_remainder",get_remainders)

#Create remainder nodes
graph_builder.add_node("check_time", check_time)
graph_builder.add_node("check_course", check_course)
graph_builder.add_node("check_extra", check_extra)
graph_builder.add_node("confirm_remainder", confirm_remainder)
graph_builder.add_node("ask_correction", ask_correction)
graph_builder.add_node("create_remainder", create_remainder)

#Core flow
graph_builder.add_edge(START,"summarizer")
graph_builder.add_edge("summarizer","intent_classifier")
graph_builder.add_conditional_edges(
    "intent_classifier",
    route_by_intent,
    {
        "RAG":"RAG",
        "remainder":"remainder_start",
        "general":"chatbot"
    }
)
graph_builder.add_conditional_edges(
    "remainder_start",
    lambda state:state['remainder_data']['operation'],
    {
        "view":"view_remainder",
        "create":"check_time"
    }
)
graph_builder.add_edge("view_remainder","remainder_end")

#Create remainder flow
#For create remainder flow, since direct jumping is needed along with HITL, we created the flow in that function
graph_builder.add_edge("create_remainder","remainder_end")
graph_builder.add_edge("remainder_end","chatbot")

graph_builder.add_edge("RAG","chatbot")
graph_builder.add_edge("chatbot",END)
graph = None

def invoke_graph(query:str,user_id,chat_id):
    config = {
        "configurable":{
            "thread_id":f'{user_id}_{chat_id}'
        }
    }
    state = graph.get_state(config)
    print(state.next)
    for task in state.tasks:
        print(task.name, task.interrupts)
    if state.next:
        response = graph.invoke(Command(resume=query),config=config)
    else:
        response = graph.invoke({"messages":query,"user_id":user_id,"chat_id":chat_id},config=config)
    if "__interrupt__" in response:
        return response['__interrupt__'][0].value
    return response['messages'][-1].text