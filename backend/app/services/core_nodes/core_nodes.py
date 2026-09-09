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
    response = retriver.get_context(state['refined_query'], top_k=10)
    return {'tool_response':response}


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
        "=== UPDATE/DELETE CONTEXT RULE ===\n"
        "For an 'update' or 'delete' operation ONLY, you MAY refer to the previous conversation to resolve references to the existing reminder being updated. "
        "This is the ONLY exception to the current-message-only rule above. "
        "If the current message clearly refers to an existing reminder using words such as 'that day', 'that date', 'same day', "
        "'on that day itself', 'same time', 'that reminder', or similar contextual references, use the previous conversation and the existing reminder context "
        "to resolve what the user means. "
        "For example, if an existing DSA reminder was previously identified as being on the 13th, and the user says "
        "'Update my remainder for DSA to 2pm on that day itself', interpret 'that day itself' as the 13th and set remainder_time to the 13th at 2:00 PM. "
        "Do NOT treat the current date as the date for 'that day' when an existing reminder date is available from the conversation. "
        "Only use previous conversation context to resolve the reference; do not use it to invent unrelated fields or change the intent. "
        "For update operations, preserve any existing reminder field that the user did not explicitly ask to change. "
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
                    "retry_message": None, "update_id": None, "delete_ids": None,
                    "change_email":None
    }}
    
def chatbot(state:State):
    tool_response = state['tool_response']
    if state["intent"] == 'remainder' and state['tool_response'] is not None:
         return {"messages":[AIMessage(content=tool_response)],"tool_response": ""}
     
    summary = state.get('summary','No summary available')
    system_prompt = SystemMessage(content=(f"""
            You are a helpful assistant for VIT students.

            Answer the user's latest message naturally and accurately.

            You have access to:

            1. Previous conversation
            2. Conversation summary
            3. The result/context produced by the current workflow

            === CURRENT WORKFLOW RESULT ===

            {tool_response if tool_response else "No workflow result available."} 
            {"Conversation intent is " + state['intent']}

            === CONVERSATION SUMMARY ===

            {summary}

            IMPORTANT RULES:

            - The CURRENT WORKFLOW RESULT is important information produced by
            the current workflow.
            - If it contains an answer or factual result relevant to the user's
            current question, you MUST incorporate that information into your
            final response.
            - Do not contradict the CURRENT WORKFLOW RESULT.
            - You may rephrase it naturally instead of copying it verbatim.
            - If the CURRENT WORKFLOW RESULT contains sources, include those sources
            apropriately in your responses, if no sources add where you get the responses from(not for remainder flow).
            - Use previous conversation context when it is relevant to the
            current question.
            - Do not mention internal implementation details such as workflow,
            state, tool_response, RAG, nodes, etc.
            """))
    return {"messages":[llm.invoke([system_prompt]+state['messages'])],"tool_response": ""}

