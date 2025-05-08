from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.agent.search_agent import SearchAgent
# from src.config.settings import settings

router = APIRouter()

# Initialize the search agent with the API key from settings
def get_search_agent():
    return SearchAgent(api_key='AIzaSyCXRW9jo3rbwcxxnt-ksWJq4aeX286Gkc0')

class QueryResponse(BaseModel):
    query: str
    ticket_summaries: list
    answer: str

@router.get("/query", response_model=QueryResponse)
async def query(search_term: str, search_agent: SearchAgent = Depends(get_search_agent)):
    try:
        results = search_agent.search(search_term)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))