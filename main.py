from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import issues
from app.middleware.timer import add_process_time_header
import os
import uvicorn

app = FastAPI(title="EduBridge AI API")

# Middleware 
app.middleware("http")(add_process_time_header)

# CORS Setup 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes 
app.include_router(issues.router)

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
