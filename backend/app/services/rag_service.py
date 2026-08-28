from app.config import settings
from sqlalchemy.orm import Session
from app.services.search_service import SearchService
from app.models.database_models import PathologyReport

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
        """Format search results as detailed medical context"""
        if not search_results:
            return "No previous pathology records retrieved for this query.\n\n"
        context = "RELEVANT MEDICAL DOCUMENTS FROM EMR DATABASE:\n\n"
        for i, result in enumerate(search_results, 1):
            context += f"Document #{i} (ID: {result.get('document_id', 'Unknown')})\n"
            context += f"  Patient Name: {result.get('patient_name', 'Unknown')}\n"
            context += f"  Patient ID / MRN: {result.get('patient_id', 'Unknown')}\n"
            context += f"  Test Type: {result.get('test_type', 'Unknown')}\n"
            context += f"  Diagnosis / Assessment: {result.get('diagnosis', 'Unknown')}\n"
            context += f"  Report Summary: {result.get('summary', 'Unknown')}\n"
            if result.get('findings'):
                context += f"  Biomarker Findings / Lab Results: {result.get('findings')}\n"
            elif result.get('text_preview'):
                context += f"  Text Content Preview: {result.get('text_preview', '')}\n"
            context += "\n"
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

            # 1. Retrieve relevant documents: Direct Patient/MRN lookup + Semantic vector search
            results_list = []
            seen_doc_ids = set()

            # A. Direct query matching for patient name, MRN, document ID, and test type
            import re
            tokens = [t for t in re.findall(r'[a-zA-Z0-9_-]+', question) if len(t) >= 3 and t.lower() not in ['summarize', 'diagnostic', 'history', 'abnormal', 'flags', 'findings', 'what', 'with', 'from', 'explain', 'show', 'tell', 'about', 'report', 'reports', 'test', 'results']]
            
            target_patient_found = False
            for token in tokens:
                matched_reports = (
                    db.query(PathologyReport)
                    .filter(
                        (PathologyReport.patient_id.ilike(f"%{token}%")) | 
                        (PathologyReport.patient_name.ilike(f"%{token}%")) | 
                        (PathologyReport.document_id.ilike(f"%{token}%")) |
                        (PathologyReport.test_type.ilike(f"%{token}%"))
                    )
                    .limit(5)
                    .all()
                )
                for r in matched_reports:
                    if r.document_id not in seen_doc_ids:
                        seen_doc_ids.add(r.document_id)
                        target_patient_found = True
                        results_list.append({
                            "document_id": r.document_id,
                            "patient_name": r.patient_name or "Unknown",
                            "patient_id": r.patient_id or "Unknown",
                            "test_type": r.test_type or "Pathology Report",
                            "diagnosis": r.diagnosis or "Normal",
                            "summary": r.summary or "Diagnostic report recorded in EMR",
                            "findings": r.findings or "",
                            "text_preview": r.summary or "",
                        })

            # B. Vector / Semantic search fallback (Only if no specific patient match was retrieved)
            if not target_patient_found:
                try:
                    search_result = SearchService.semantic_search(db, question, top_k=3)
                    if search_result.get("status") == "success":
                        for res in search_result.get("results", []):
                            doc_id = res.get("document_id")
                            if doc_id and doc_id not in seen_doc_ids:
                                seen_doc_ids.add(doc_id)
                                results_list.append(res)
                except Exception as search_err:
                    print(f"[WARN] Vector search lookup skipped: {search_err}")

            # C. If still 0 documents found, check if there are existing reports in DB as contextual fallback
            if len(results_list) == 0:
                all_recent = db.query(PathologyReport).order_by(PathologyReport.created_at.desc()).limit(3).all()
                for r in all_recent:
                    pname = (r.patient_name or "").lower()
                    diag = (r.diagnosis or "").lower()
                    ttype = (r.test_type or "").lower()
                    q_lower = question.lower()
                    if any(part in q_lower for part in pname.split() if len(part) > 2) or any(part in q_lower for part in ttype.split() if len(part) > 2):
                        if r.document_id not in seen_doc_ids:
                            seen_doc_ids.add(r.document_id)
                            results_list.append({
                                "document_id": r.document_id,
                                "patient_name": r.patient_name or "Unknown",
                                "patient_id": r.patient_id or "Unknown",
                                "test_type": r.test_type or "Pathology Report",
                                "diagnosis": r.diagnosis or "Normal",
                                "summary": r.summary or "Diagnostic report recorded in EMR",
                                "findings": r.findings or "",
                                "text_preview": r.summary or "",
                            })

            # 2. Format context from search results
            context = self.format_search_results(results_list)

            # 3. Build conversation messages with strict domain guardrails
            system_message = """You are the AI Datrix Clinical AI Assistant, an expert medical pathology intelligence system built specifically for the AI-Based EMR Pathology Report Management System.

STRICT DOMAIN SCOPE & GUARDRAILS:
1. EXCLUSIVE MEDICAL PATHOLOGY DOMAIN:
   - You MUST ONLY answer questions concerning medical pathology, diagnostic laboratory reports (e.g., Complete Blood Count / CBC, Liver Function Tests / LFT, Renal Function Tests / RFT, Lipid Profiles, Urinalysis, Biopsies, Biochemical panels), clinical biomarkers, reference ranges, abnormal flags, and the architectural operation of the AI Datrix platform.

2. STRICT REFUSAL OF OUT-OF-SCOPE QUERIES:
   - If the user asks ANY question outside of medicine, pathology, or the AI Datrix system (such as writing general code/programming, "what is python", general math, recipes, poems, jokes, movies, politics, sports, gaming, or general chit-chat):
   - You MUST POLITELY DECLINE and state that you are exclusively configured for pathology analysis.
   - Refusal standard: "I am the AI Datrix Clinical Assistant, specialized exclusively in pathology laboratory reports, diagnostic biomarkers, and EMR patient records. I cannot assist with general programming or non-medical topics. Please ask a question regarding patient pathology tests or clinical laboratory data."

3. GROUNDING IN EMR DATA:
   - When pathology documents are provided in the context below, ground your clinical answers strictly in those documents and cite the patient name, MRN, or document ID.
   - If a medical question asks for a specific patient's report that is not in the context, explicitly state: "No corresponding pathology records were found in the EMR vault for this patient/query." Do not fabricate or hallucinate medical numbers.

4. GREETINGS & IDENTITY:
   - If the user greets you (e.g. "hello", "hi", "who are you"), respond politely, state your clinical purpose as the AI Datrix Pathology Assistant, and invite them to query laboratory findings or patient records.

5. TONE:
   - Professional, clinically precise, concise, and focused strictly on pathology diagnostics."""

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
            candidate_models = ["llama-3.3-70b-versatile", self.groq_model, "groq/compound-mini", "groq/compound", "qwen/qwen3.6-27b"]
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
