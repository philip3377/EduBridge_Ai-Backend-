from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import issues
from app.middleware.timer import add_process_time_header

app = FastAPI(title="EduBridge AI API")

# Middleware တပ်ဆင်ခြင်း
app.middleware("http")(add_process_time_header)

# CORS Setup (React Frontend အတွက်)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes များအား ချိတ်ဆက်ခြင်း
app.include_router(issues.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)