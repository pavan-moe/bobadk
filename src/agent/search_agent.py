from typing import List, Dict, Any, Set
import os
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

class SearchAgent:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.qdrant_client = QdrantClient(
            url=os.environ.get("QDRANT_URL", "http://localhost:6333"),
            api_key=os.environ.get("QDRANT_API_KEY")
        )
        self.collection_name = "zendesk"
        
        # Initialize ADK agent
        self.agent = Agent(
            name="zendesk_search_agent",
            model="gemini-1.5-pro",  # Use the appropriate model
            description="Agent to answer questions using Zendesk ticket data.",
            instruction="You are an expert customer support analyst. Answer questions based only on the provided ticket summaries. Be precise and helpful."
        )
        
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            app_name="ZendeskSupportApp",
            agent=self.agent,
            session_service=self.session_service
        )

    def search(self, query: str, limit: int = 5):
        # Step 1: Perform the vector search to get relevant chunks
        search_results = self.vector_search(query, limit)
        
        # Step 2: Extract ticket_ids from search results
        ticket_ids = self.extract_ticket_ids(search_results)
        
        # Step 3: Fetch all chunks related to each ticket_id
        complete_tickets = self.fetch_complete_tickets(ticket_ids)
        
        # Step 4: Reconstruct and summarize tickets
        ticket_summaries = self.summarize_tickets(complete_tickets)
        
        # Step 5: Use agent to generate a response based on query and summaries
        final_answer = self.generate_answer(query, ticket_summaries)
        
        return {
            "query": query,
            "ticket_summaries": ticket_summaries,
            "answer": final_answer
        }

    def vector_search(self, query: str, limit: int = 5) -> List[Dict[Any, Any]]:
        """Perform vector search in Qdrant"""
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_text=query,
            limit=limit
        )
        return results
    
    def extract_ticket_ids(self, search_results: List[Dict[Any, Any]]) -> Set[str]:
        """Extract unique ticket_ids from search results"""
        ticket_ids = set()
        for result in search_results:
            if 'payload' in result and 'ticket_id' in result['payload']:
                ticket_ids.add(result['payload']['ticket_id'])
        return ticket_ids
    
    def fetch_complete_tickets(self, ticket_ids: Set[str]) -> Dict[str, List[Dict]]:
        """Fetch all chunks for each ticket_id"""
        complete_tickets = {}
        
        for ticket_id in ticket_ids:
            # Use Qdrant filter to get all chunks for this ticket_id
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="ticket_id",
                        match=MatchValue(value=ticket_id)
                    )
                ]
            )
            
            chunks = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                filter=filter_condition,
                limit=100
            )[0]  # scroll returns (results, next_page_offset)
            
            complete_tickets[ticket_id] = chunks
            
        return complete_tickets
    
    def summarize_tickets(self, complete_tickets: Dict[str, List[Dict]]) -> List[Dict]:
        """Reconstruct and summarize each ticket"""
        summaries = []
        
        for ticket_id, chunks in complete_tickets.items():
            # Sort chunks by some order if needed (e.g., timestamp or chunk_id)
            # chunks.sort(key=lambda x: x.get('payload', {}).get('timestamp', 0))
            
            # Combine all text from chunks
            full_text = " ".join([chunk.get('payload', {}).get('text', '') for chunk in chunks])
            
            # Create a new session for summarization
            session = self.session_service.create_session(
                app_name="ZendeskSupportApp",
                user_id="system",
                session_id=f"summarize_{ticket_id}"
            )
            
            # Generate summary using the agent
            response = self.runner.run(
                session=session,
                message=f"Summarize the following support ticket concisely: {full_text}"
            )
            
            summary = response.text if response else "No summary available"
            
            # Get metadata from chunks
            metadata = {}
            if chunks and 'payload' in chunks[0]:
                metadata = {k: v for k, v in chunks[0]['payload'].items() 
                           if k != 'text' and k != 'vector'}
            
            summaries.append({
                "ticket_id": ticket_id,
                "summary": summary,
                "metadata": metadata
            })
            
        return summaries
    
    def generate_answer(self, query: str, ticket_summaries: List[Dict]) -> str:
        """Generate a final answer using the agent based on the query and ticket summaries"""
        # Format summaries for the agent
        formatted_summaries = "\n\n".join([
            f"Ticket {i+1} (ID: {summary['ticket_id']}):\n{summary['summary']}"
            for i, summary in enumerate(ticket_summaries)
        ])
        
        # Create a new session for answering
        session = self.session_service.create_session(
            app_name="ZendeskSupportApp",
            user_id="user",
            session_id=f"answer_{hash(query)}"
        )
        
        # Generate answer using the agent
        prompt = f"""
        Based only on the following ticket summaries, answer this question: {query}
        
        TICKET SUMMARIES:
        {formatted_summaries}
        
        Answer:
        """
        
        response = self.runner.run(
            session=session,
            message=prompt
        )
        
        return response.text if response else "No answer could be generated."
        
    def perform_search(self, query):
        """Legacy method for backward compatibility"""
        return self.search(query)