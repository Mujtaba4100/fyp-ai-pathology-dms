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
        if not search_results:
            return "No previous pathology records retrieved for this query.\n\n"
        context = "RELEVANT MEDICAL DOCUMENTS FROM EMR DATABASE:\n\n"
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
                    "message": "Groq client not configured or API key is missing.",
                    "answer": "Error: Groq client not configured. Please set GROQ_API_KEY in .env.",
                    "source_documents": [],
                }

            # 1. Retrieve semantically relevant documents if available in DB
            results_list = []
            try:
                search_result = SearchService.semantic_search(db, question, top_k=3)
                if search_result.get("status") == "success":
                    results_list = search_result.get("results", [])
            except Exception as search_err:
                print(f"[WARN] Vector search lookup skipped: {search_err}")

            # 2. Format context from search results
            context = self.format_search_results(results_list)

            # 3. Build conversation messages
            system_message = """You are AI Datrix Clinical AI Assistant, an expert medical pathology intelligence system.
Rules:
1. When pathology documents are provided in context, strictly ground your clinical answers in those documents and cite the patient name or document ID.
2. If no specific patient documents are attached or if the user asks a general question or greeting (like "hello", "hi"), answer politely, professionally, and clearly.
3. Be concise, objective, and clinically accurate."""

            user_message = f"{context}\nUser Question: {question}"

            messages = [{"role": "system", "content": system_message}]

            # Add conversation history if any
            if conversation_history:
                for msg in conversation_history:
                    if msg.get("content"):
                        messages.append({"role": msg.get("role", "user"), "content": msg["content"]})

            # Add current context and question
            messages.append({"role": "user", "content": user_message})

            # 4. Request completions from Groq with model fallback
            candidate_models = [self.groq_model, "groq/compound-mini", "groq/compound", "qwen/qwen3.6-27b", "openai/gpt-oss-120b"]
            last_err = None

            for model_name in candidate_models:
                try:
                    response = self.groq_client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0.2,
                        max_tokens=1000,
                    )

                    answer = response.choices[0].message.content or ""

                    return {
                        "status": "success",
                        "answer": answer.strip(),
                        "source_documents": results_list,
                        "total_sources": len(results_list),
                    }
                except Exception as err:
                    last_err = err
                    continue

            raise last_err or Exception("RAG query failed across all candidate models")

        except Exception as e:
            return {
                "status": "error",
                "message": f"RAG Service failed: {str(e)}",
                "answer": f"Error: Chatbot failed to process question: {str(e)}",
                "source_documents": [],
            }
