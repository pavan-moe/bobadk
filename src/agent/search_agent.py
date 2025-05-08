from typing import List, Dict, Any, Set
import os
import json
from openai import AzureOpenAI  # Azure OpenAI client
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from qdrant_client import models

class SearchAgent:
    def __init__(self, api_key='AIzaSyCXRW9jo3rbwcxxnt-ksWJq4aeX286Gkc0'):
        self.api_key = 'AIzaSyCXRW9jo3rbwcxxnt-ksWJq4aeX286Gkc0'
        
        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            url='http://172.16.0.25:6333',
        )
        self.collection_name = "zendesk"
        
        # Initialize Azure OpenAI client
        self.azure_openai_client = AzureOpenAI(
            api_key='fbaa385dfb154b24a72d881950acee0d',  
            azure_endpoint='https://moeazureopenaiapi.openai.azure.com',
            api_version='2023-05-15',
        )
        self.embedding_deployment = 'embedding-model'
        
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

    def search(self, query: str, limit: int = 1):
        try:
            # Step 1: Perform the vector search to get relevant chunks
            search_results = self.vector_search(query, limit)
            
            # Step 2: Extract ticket_ids from search results
            ticket_ids = self.extract_ticket_ids(search_results)
            
            if not ticket_ids:
                return {
                    "query": query,
                    "ticket_summaries": [],
                    "answer": "I couldn't find any relevant information in the ticket database."
                }
            
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
        except Exception as e:
            print(f"Error in search: {str(e)}")
            return {
                "query": query,
                "ticket_summaries": [],
                "answer": f"An error occurred during search: {str(e)}"
            }

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embeddings using Azure OpenAI"""
        try:

            response = self.azure_openai_client.embeddings.create(
                input=text,
                model=self.embedding_deployment
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            raise

    def vector_search(self, query: str, limit: int = 5) -> List[Dict[Any, Any]]:
        """Perform vector search in Qdrant using Azure OpenAI embeddings"""
        # Generate embedding for the query
        query_vector = self.generate_embedding(query)
        
        # Search Qdrant using the embedding vector
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return results
    
    def extract_ticket_ids(self, search_results: List[Dict[Any, Any]]) -> Set[str]:
        """Extract unique ticket_ids from search results"""
        ticket_ids = set()
        
        try:
            for result in search_results:
                # The structure of search_results depends on Qdrant client version
                # For newer Qdrant client versions (>1.1.0)
                if hasattr(result, 'payload') and result.payload is not None:
                    if 'ticket_id' in result.payload:
                        ticket_ids.add(result.payload['ticket_id'])
                # For older versions or different return type
                elif isinstance(result, dict) and 'payload' in result:
                    if 'ticket_id' in result['payload']:
                        ticket_ids.add(result['payload']['ticket_id'])
            
            return ticket_ids
        except Exception as e:
            print(f"Error extracting ticket IDs: {str(e)}")
            print(f"Search results structure: {type(search_results)}")
            if search_results:
                print(f"First result type: {type(search_results[0])}")
                print(f"First result: {search_results[0]}")
            return set() 
    
    
    def fetch_complete_tickets(self, ticket_ids: Set[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all chunks for each ticket_id using metadata filtering without embeddings."""
        complete_tickets = {}

        for ticket_id in ticket_ids:
            try:
                # Build the scroll_filter using Qdrant models
                scroll_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="ticket_id",
                            match=models.MatchValue(value=ticket_id)
                        )
                    ]
                )

                points = []
                offset = None  # Use None for initial scroll offset
                batch_size = 100

                while True:
                    response = self.qdrant_client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=scroll_filter,
                        limit=batch_size,
                        offset=offset
                    )

                    if not response:
                        # No more points to fetch
                        break

                    points.extend(response)

                    if len(response) < batch_size:
                        # Fetched last batch
                        break

                    # Update offset for next scroll call
                    offset = len(points)

                complete_tickets[ticket_id] = points
                print(f"Fetched {len(points)} chunks for ticket {ticket_id}")

            except Exception as e:
                print(f"Error fetching chunks for ticket {ticket_id}: {str(e)}")
                continue

        print(f"Fetched {len(complete_tickets)} complete tickets.")
        return complete_tickets
        
    def summarize_tickets(self, complete_tickets: Dict[str, List[Dict]]) -> List[Dict]:
        """Reconstruct and summarize each ticket"""
        summaries = []
        
        for ticket_id, chunks in complete_tickets.items():
            # Sort chunks by some order if needed (e.g., timestamp)
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
        if not ticket_summaries:
            return "I couldn't find any relevant information to answer your question."
            
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