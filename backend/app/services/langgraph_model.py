from datetime import datetime
from typing import Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict, Annotated
from dotenv import load_dotenv
load_dotenv()
def merge_dict(old: dict | None, new: dict | None) -> dict:
    if old is None:
        return new
    if new is None:
        return old
    return {**old, **new}

def last_val(old:str ,new:str)->str:
    return new

class RemainderData(TypedDict):
    operation: Annotated[str, ..., "One of 'view','create', 'update', 'delete' — what the user wants done with the remainder"]
    course_name: Annotated[str, ..., "Name of the course for which remainder has to be created, updated, or deleted"]
    remainder_time: Optional[datetime]
    time_mentioned: Annotated[bool, ..., "True only if the user's query contains an actual date/time reference (e.g. 'tomorrow', 'next Monday', '5pm', 'on the 20th'). False if no date/time was mentioned at all."]
    event_type: Annotated[Optional[str], ..., "Type of event, e.g. 'quiz', 'assignment', 'project review', 'class'. Null if not mentioned."]
    extra_info: Annotated[Optional[str], ..., "Any extra detail the user gave, e.g. syllabus portions, topics, or notes. Null if not mentioned."]
    
class State(TypedDict):
    summary:str
    messages: Annotated[list, add_messages]
    intent: Annotated[str, ..., "Should indicate the intent of user query only from [RAG,remainder,general]"]
    refined_query: Annotated[str, ..., "Refine the query incase the intent is to query RAG without changing the context"]
    remainder_data: Annotated[RemainderData, merge_dict]
    tool_response: Annotated[str,last_val]
    user_id: int
    chat_id: int

class IntentRespone(TypedDict):
    """Request data format"""
    intent: Annotated[str, ..., "Should indicate the intent of user query only from [RAG,remainder,general], anything related to academics comes under RAG"]
    refined_query: Annotated[str, ..., "Refine the query incase the intent is to query RAG without changing the context"]
    remainder_data: RemainderData