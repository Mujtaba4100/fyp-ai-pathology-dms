from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.schemas import MessageResponse, HealthResponse
from app.routes import auth, upload, ocr, text_cleaning, llm_extraction

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Based Pathology Report Management",
    debug=settings.DEBUG
)

# Allow frontend (React/Flutter) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(ocr.router)
app.include_router(text_cleaning.router)
app.include_router(llm_extraction.router)

@app.get("/", response_model=MessageResponse)
async def root():
    return {"message": "Hello"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok", "message": "System is healthy"}
