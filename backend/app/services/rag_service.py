from app.config import settings
from sqlalchemy.orm import Session
from app.services.search_service import SearchService

try:
    from groq import Groq
except ImportError:
    Groq = None


class RAGService:
    """RAG (Retrieval Augmented Generation) service for chatbot Q&A"""

    def __init__(self):
        self.groq_client = (
            Groq(api_key=settings.GROQ_API_KEY)
            if (
                Groq
                and settings.GROQ_API_KEY
                and settings.GROQ_API_KEY != "gsk_change_me_to_your_groq_key"
            )
            else None
        )
        self.groq_model = settings.GROQ_MODEL

    @staticmethod
    def format_search_results(search_results: list) -> str:
        """Format search results as context"""
        context = "RELEVANT MEDICAL DOCUMENTS:\n\n"
        for i, result in enumerate(search_results, 1):
            context += f"Document #{i} (ID: {result.get('document_id', 'Unknown')})\n"
            context += f"  Patient Name: {result.get('patient_name', 'Unknown')}\n"
            context += f"  Test Type: {result.get('test_type', 'Unknown')}\n"
            context += f"  Diagnosis: {result.get('diagnosis', 'Unknown')}\n"
            context += f"  Report Summary: {result.get('summary', 'Unknown')}\n"
            context += f"  Text Content Preview: {result.get('text_preview', '')}\n\n"
        return context

    def answer_question(
        self, db: Session, question: str, conversation_history: list = None
    ) -> dict:
        """Answer user question using RAG and Groq"""
        try:
            if not self.groq_client:
                return {
                    "status": "error",
                    "message": "Groq client not configured or API key is missing/placeholder.",
                    "answer": "Error: Groq client not configured. Please set GROQ_API_KEY in .env.",
                    "source_documents": [],
                }

            # 1. Retrieve the most semantically relevant documents
            search_result = SearchService.semantic_search(db, question, top_k=3)

            if search_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Search failed: {search_result.get('message')}",
                    "answer": "Error: Failed to retrieve relevant documents.",
                    "source_documents": [],
                }

            results_list = search_result.get("results", [])
            if not results_list:
                return {
                    "status": "no_results",
                    "message": "No relevant documents found",
                    "answer": "I could not find any relevant documents in the EMR database to answer your question.",
                    "source_documents": [],
                }

            # 2. Format context from search results
            context = self.format_search_results(results_list)

            # 3. Build conversation messages
            system_message = """You are a medical AI assistant that answers questions about pathology reports based on retrieved documents.
            
Rules:
1. ONLY answer based on the provided documents.
2. If the answer is not in the documents, say "I don't have this information in the available documents."
3. Be concise, objective, and medically accurate.
4. Always cite which document (use patient name or ID) the answer comes from.
5. Do not make up or hallucinate information."""

            user_message = f"{context}\n\nQuestion: {question}\n\nBased on the medical documents above, please answer this question."

            messages = [{"role": "system", "content": system_message}]

            # Add conversation history if any
            if conversation_history:
                for msg in conversation_history:
                    messages.append(msg)

            # Add current context and question
            messages.append({"role": "user", "content": user_message})

            # 4. Request completions from Groq
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                temperature=0.2,  # Low temperature for factual consistency
                max_tokens=1000,
            )

            answer = response.choices[0].message.content or ""

            return {
                "status": "success",
                "answer": answer.strip(),
                "source_documents": results_list,
                "total_sources": len(results_list),
                "cost_estimate": "$0.000000 (Evaluations/Free Tier/Low Cost)",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"RAG Service failed: {str(e)}",
                "answer": f"Error: Chatbot failed to process question: {str(e)}",
                "source_documents": [],
            }
