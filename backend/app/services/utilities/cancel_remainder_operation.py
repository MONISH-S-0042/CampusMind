from dotenv import load_dotenv
from langgraph.types import Command
load_dotenv()

CANCEL_PHRASES = {"cancel", "stop", "nevermind", "never mind", "quit", "exit", "abort", "cancel remainder"}

def is_cancel(answer) -> bool:
    return str(answer).strip().lower() in CANCEL_PHRASES

def cancelled_command(msg:str):
    return Command(
        goto="remainder_end",
        update={
            "tool_response": msg,
        },
    )