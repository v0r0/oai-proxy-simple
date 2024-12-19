from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import httpx

app = FastAPI()

OPENAI_BASE_URL = "https://api.openai.com"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Missing or invalid Authorization header.")
        user_api_key = auth_header.split(" ", 1)[1]

        is_streaming = body.get("stream", False)

        headers = {
            "Authorization": f"Bearer {user_api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if is_streaming:
                async with client.stream(
                    "POST",
                    f"{OPENAI_BASE_URL}/v1/chat/completions",
                    headers=headers,
                    json=body
                ) as response:
                    response.raise_for_status()

                    async def stream_generator():
                        async for line in response.aiter_lines():
                            yield line
                    return StreamingResponse(stream_generator(), media_type="text/event-stream")
            else:
                response = await client.post(
                    f"{OPENAI_BASE_URL}/v1/chat/completions",
                    headers=headers,
                    json=body
                )
                response.raise_for_status()
                return JSONResponse(content=response.json(), status_code=response.status_code)

    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with OpenAI: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=80)
