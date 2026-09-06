from datetime import datetime

import dateparser
from langchain_core.messages import AIMessage, HumanMessage,SystemMessage, RemoveMessage
import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from app.RAG.operations.retrival_pipeline import get_retrival_pipeleine
from app.services.langgraph_model import IntentRespone, State
from app.services.utilities.time import IST, to_local_time
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

def get_chat_bot(llm_name:str):
    llm = init_chat_model(model=llm_name)
    return llm

def RAG_tool(state:State):
    """Answers queries related to VIT rules and regulations using the retrieval pipeline,
    driven by 'refined_query' already present in state.

    Returns:
        dict: Updates 'tool_response' with the retrieved answer.
    """
    retriver = get_retrival_pipeleine()
    response = retriver.process_query(state['refined_query'], top_k=10)
    return {'tool_response':response.get("answer")}


llm = get_chat_bot("google_genai:gemini-3.5-flash-lite") 
intent_llm = get_chat_bot("groq:openai/gpt-oss-120b")
structured_agent = intent_llm.with_structured_output(IntentRespone,method='json_mode')

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
    now = datetime.now(IST).isoformat()
    system_prompt = SystemMessage(content=(
        "You are an intent classifier for a VIT student assistant. "
        f"The current date and time is {now}. "
        "\n\n"
        "=== OUTPUT FORMAT — STRICT ===\n"
        "Respond with ONLY a JSON object. It MUST contain exactly these top-level keys, always, with no exceptions: "
        "intent, refined_query, remainder_data.\n"
        "remainder_data MUST always contain exactly these keys, in every single response, even when a value is null or false: "
        "operation, course_name, time_mentioned, remainder_time, event_type, extra_info.\n"
        "NEVER omit a key. If a value doesn't apply, include the key anyway with null (or false for time_mentioned) — "
        "a missing key is treated as an error.\n"
        "\n"
        "=== EXAMPLE OF A CORRECT RESPONSE (structure only — copy this shape exactly) ===\n"
        '{"intent": "remainder", "refined_query": "Create reminder for DSA quiz", '
        '"remainder_data": {"operation": "create", "course_name": "DSA", "time_mentioned": false, '
        '"remainder_time": null, "event_type": "quiz", "extra_info": null}}\n"'
        "Notice time_mentioned and remainder_time are BOTH present even though nothing about time was said.\n"
        "\n"
        "=== SCOPE RULE ===\n"
        "Classify intent and extract ALL fields based ONLY on the most recent user message's own wording. "
        "Do not let earlier turns bias intent or remainder_data, even if recent turns were about reminders — "
        "a new unrelated message (e.g. about rules, policies, or general questions) must be classified independently, "
        "unless it is clearly answering a question you just asked, or the user explicitly says to use earlier context.\n"
        "\n"
        "=== INTENT VALUES ===\n"
        "intent: one of 'RAG', 'remainder', 'general'. "
        "Anything about academics, hostels, mess, or examinations assume it as 'RAG'.\n"
        "\n"
        "=== remainder_data.operation ===\n"
        "'create' — setting a new reminder. "
        "'view' — listing/checking existing reminders. "
        "'update' — changing an existing reminder's time/details. "
        "'delete' — cancelling a reminder.\n"
        "\n"
        "=== remainder_data.time_mentioned (decide this FIRST, before remainder_time) ===\n"
        "Set to true ONLY if the CURRENT message's exact words contain a date/time reference "
        "(e.g. 'tomorrow', 'next Monday', '5pm', 'on the 20th', 'day after tomorrow'). "
        "Set to false if the current message says nothing about when. "
        "This key must be present as an explicit true or false — never omit it.\n"
        "\n"
        "=== remainder_data.remainder_time (decide AFTER time_mentioned, using its value) ===\n"
        "If time_mentioned is false: remainder_time MUST be null. Do not guess a date.\n"
        "If time_mentioned is true and only a date was given (no clock time): resolve the date relative to the "
        "current date/time above, and set the time portion to 08:00:00.\n"
        "If time_mentioned is true and both date and time were given: use exactly what was said.\n"
        "\n"
        "=== remainder_data.event_type ===\n"
        "One of 'quiz', 'assignment', 'project review', 'class', or null if not mentioned.\n"
        "\n"
        "=== remainder_data.extra_info ===\n"
        "Any additional detail given (syllabus portions, topics to cover). "
        "Must NOT contain the course name or any time/date reference — those belong in their own fields. "
        "Null if nothing extra was given."
    ))
    
    
    recent = state['messages'][-2:]  
    summary_message = HumanMessage(content=f"Earlier conversation summary: {state.get('summary', 'No summary available')}")
    result = structured_agent.invoke([system_prompt] + [summary_message] + recent)
    print(result)
    remainder_data = result["remainder_data"]
    raw_time = remainder_data.get("remainder_time")
    if isinstance(raw_time, str):
        parsed = dateparser.parse(
            raw_time, 
            settings={
                "RELATIVE_BASE": datetime.now(IST),
                "PREFER_DATES_FROM": "future"
            })
        remainder_data["remainder_time"] = to_local_time(parsed) if parsed else None
    elif raw_time is not None:
        remainder_data["remainder_time"] = to_local_time(raw_time)

    time_mentioned = remainder_data.get("time_mentioned", True)
    if not time_mentioned:
        remainder_data["remainder_time"] = None
    return {
        "intent": result["intent"],
        "refined_query": result["refined_query"],
        "remainder_data": remainder_data,
    }

def route_by_intent(state:State):
    if(state['intent'] == 'RAG'):
        return "RAG"
    elif state['intent']=='remainder':
        return "remainder"
    return "general"

def remainder_operation(state:State):
    print("Entering remainder flow...")
    return {}
def remainder_end(state:State):
    print("Exiting Remainder Flow")
    return {"remainder_data": {
                    "operation": None, "course_name": None, "time_mentioned": None,
                    "remainder_time": None, "event_type": None, "extra_info": None,
                    "retry_message": None,
    }}
    
def chatbot(state:State):
    if state['intent']!='general' and state['tool_response']!='Not Found in Documents':
        return {"messages":[AIMessage(content=state['tool_response'])]}
    system_prompt = SystemMessage(content=(
        "You are a helpful assistant for VIT students. Assume every HumanMessage query is related to VIT. "
        "Answer as accurately and helpfully as you can based only on previous context if they contains the answer else using your own knowledge."
        "Important Note: Include the source of your answer(From previous context or From Web Search appropriately) at the start of the answer"
    ))
    return {"messages":[llm.invoke([system_prompt]+[f"Earlier conversation summary:{state.get('summary','No summary available')}"]+state['messages'])],"tool_response": ""}

