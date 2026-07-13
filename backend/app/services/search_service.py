from sqlalchemy.orm import Session
from app.models.database_models import DocumentEmbedding, PathologyReport
from app.services.embedding_service import EmbeddingService

class SearchService:
    """Service for performing semantic and keyword searches on medical documents."""

    @staticmethod
    def semantic_search(db: Session, query_text: str, top_k: int = 5) -> dict:
        try:
            # 1. Generate query embedding locally (384 dimensions)
            embedding_service = EmbeddingService()
            emb_res = embedding_service.generate_embedding(query_text)
            if emb_res["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Query embedding generation failed: {emb_res.get('message')}",
                    "results": []
                }
            
            query_embedding = emb_res["embedding"]

            # 2. Perform distance search using pgvector's native l2_distance operator
            # Lower distance means closer similarity
            distance_expr = DocumentEmbedding.embedding.l2_distance(query_embedding)
            similar_embeddings = (
                db.query(DocumentEmbedding, distance_expr.label("distance"))
                .order_by("distance")
                .limit(top_k)
                .all()
            )

            results = []
            for doc_emb, distance in similar_embeddings:
                # Convert distance to similarity score: 1 / (1 + distance)
                similarity = 1 / (1 + float(distance))
                
                # Fetch matching pathology report
                report = db.query(PathologyReport).filter(
                    PathologyReport.document_id == doc_emb.document_id
                ).first()

                results.append({
                    "document_id": doc_emb.document_id,
                    "similarity_score": round(similarity, 4),
                    "distance": round(float(distance), 4),
                    "text_preview": doc_emb.text_chunk[:200] if doc_emb.text_chunk else "",
                    "patient_name": report.patient_name if report else "Unknown",
                    "patient_id": report.patient_id if report else "Unknown",
                    "test_type": report.test_type if report else "Unknown",
                    "diagnosis": report.diagnosis if report else "Unknown",
                    "summary": report.summary if report else "No summary"
                })

            return {
                "status": "success",
                "query": query_text,
                "total_results": len(results),
                "results": results
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Semantic search failed: {str(e)}",
                "results": []
            }

    @staticmethod
    def keyword_search(db: Session, keyword: str, top_k: int = 5) -> dict:
        try:
            # Simple SQL ILIKE search in pathology reports
            reports = (
                db.query(PathologyReport)
                .filter(
                    (PathologyReport.diagnosis.ilike(f"%{keyword}%")) |
                    (PathologyReport.summary.ilike(f"%{keyword}%")) |
                    (PathologyReport.test_type.ilike(f"%{keyword}%")) |
                    (PathologyReport.findings.ilike(f"%{keyword}%"))
                )
                .limit(top_k)
                .all()
            )

            results = []
            for report in reports:
                results.append({
                    "document_id": report.document_id,
                    "patient_name": report.patient_name,
                    "patient_id": report.patient_id,
                    "test_type": report.test_type,
                    "diagnosis": report.diagnosis,
                    "summary": report.summary
                })

            return {
                "status": "success",
                "keyword": keyword,
                "total_results": len(results),
                "results": results
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Keyword search failed: {str(e)}",
                "results": []
            }
