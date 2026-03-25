from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Simple API is running"}

@app.post("/test")
async def test_endpoint():
    return {"message": "Test endpoint works!"}
