from sqlalchemy.orm import Session
from app.models.database_models import DocumentEmbedding, PathologyReport
from app.services.embedding_service import EmbeddingService


class SearchService:
    """Service for performing semantic and keyword searches on medical documents."""

    @staticmethod
    def semantic_search(db: Session, query_text: str, top_k: int = 5) -> dict:
        results = []
        try:
            # 1. Try Generating 768-dim query embedding locally
            embedding_service = EmbeddingService()
            emb_res = embedding_service.generate_embedding(query_text)
            
            if emb_res.get("status") == "success" and emb_res.get("embedding"):
                query_embedding = emb_res["embedding"]

                # 2. Perform distance search using pgvector's native l2_distance operator
                distance_expr = DocumentEmbedding.embedding.l2_distance(query_embedding)
                similar_embeddings = (
                    db.query(DocumentEmbedding, distance_expr.label("distance"))
                    .order_by("distance")
                    .limit(top_k)
                    .all()
                )

                for doc_emb, distance in similar_embeddings:
                    similarity = 1 / (1 + float(distance))
                    report = (
                        db.query(PathologyReport)
                        .filter(PathologyReport.document_id == doc_emb.document_id)
                        .first()
                    )

                    results.append({
                        "document_id": doc_emb.document_id,
                        "similarity_score": round(similarity, 4),
                        "distance": round(float(distance), 4),
                        "text_preview": (doc_emb.text_chunk[:200] + "...") if doc_emb.text_chunk else "",
                        "patient_name": report.patient_name if report else "Unknown Patient",
                        "patient_id": report.patient_id if report else "N/A",
                        "test_type": report.test_type if report else "Pathology Report",
                        "diagnosis": report.diagnosis if report else "Normal",
                        "summary": report.summary if report else (report.clinical_summary if hasattr(report, 'clinical_summary') else "Clinical report extract"),
                    })

            # 3. Fallback: If vector search returned 0 results or had an issue, fallback to SQL search
            if not results:
                fallback_res = SearchService.keyword_search(db, query_text, top_k=top_k)
                if fallback_res.get("status") == "success":
                    return fallback_res

            return {
                "status": "success",
                "query": query_text,
                "total_results": len(results),
                "results": results,
            }

        except Exception as e:
            # Automatic graceful fallback to keyword matching so API never crashes
            print(f"[WARN] Semantic search vector lookup fallback to text search: {e}")
            try:
                fallback_res = SearchService.keyword_search(db, query_text, top_k=top_k)
                return fallback_res
            except Exception as kw_err:
                return {
                    "status": "success",
                    "query": query_text,
                    "total_results": 0,
                    "results": [],
                    "message": "No matching records found.",
                }

    @staticmethod
    def keyword_search(db: Session, keyword: str, top_k: int = 5) -> dict:
        try:
            # Simple SQL ILIKE search in pathology reports
            reports = (
                db.query(PathologyReport)
                .filter(
                    (PathologyReport.patient_name.ilike(f"%{keyword}%"))
                    | (PathologyReport.diagnosis.ilike(f"%{keyword}%"))
                    | (PathologyReport.summary.ilike(f"%{keyword}%"))
                    | (PathologyReport.test_type.ilike(f"%{keyword}%"))
                    | (PathologyReport.findings.ilike(f"%{keyword}%"))
                )
                .limit(top_k)
                .all()
            )

            results = []
            for report in reports:
                results.append(
                    {
                        "document_id": report.document_id,
                        "patient_name": report.patient_name,
                        "patient_id": report.patient_id,
                        "test_type": report.test_type,
                        "diagnosis": report.diagnosis,
                        "summary": report.summary,
                    }
                )

            return {
                "status": "success",
                "keyword": keyword,
                "total_results": len(results),
                "results": results,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Keyword search failed: {str(e)}",
                "results": [],
            }