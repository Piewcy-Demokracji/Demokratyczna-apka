from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.user import Base
from app.core.database import engine
from app.api import auth, polls

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Voting App API",
    description="A voting application API",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(polls.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Voting App API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
