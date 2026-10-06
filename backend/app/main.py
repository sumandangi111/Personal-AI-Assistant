from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .ai_service import extract_memories, extract_local_memory
from .database import Base, engine
from .auth import router as auth_router
from .chat import router as chat_router
from .memory import router as memory_router
from .gmail import router as gmail_router
from .calendar import router as calendar_router
from .admin import router as admin_router
from .meeting import router as meeting_router


# -----------------------------------------------------
# Database
# -----------------------------------------------------

Base.metadata.create_all(bind=engine)


# -----------------------------------------------------
# FastAPI Application
# -----------------------------------------------------

app = FastAPI(
    title="Personal AI Assistant"
)


# -----------------------------------------------------
# CORS
# -----------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------
# Routers
# -----------------------------------------------------

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(memory_router)
app.include_router(gmail_router)
app.include_router(calendar_router)
app.include_router(admin_router)
app.include_router(meeting_router)

# -----------------------------------------------------
# Root
# -----------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Personal AI Assistant API is running"
    }


# -----------------------------------------------------
# Health
# -----------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# -----------------------------------------------------
# Test AI Memory Extraction
# -----------------------------------------------------

@app.post("/test-memory")
def test_memory(message: str):

    result = extract_memories(message)

    return {
        "message": message,
        "extracted_memory": result
    }


# -----------------------------------------------------
# Test Local Memory Extraction
# -----------------------------------------------------

@app.post("/test-local-memory")
def test_local_memory(message: str):

    result = extract_local_memory(message)

    return {
        "message": message,
        "extracted_memory": result
    }