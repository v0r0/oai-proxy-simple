from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
import json

app = FastAPI()

UPSTREAM_API_URL = "https://api.openai.com/v1/chat/completions"


@app.post("/v1/chat/completions")
async def proxy_response(request: Request, authorization: str = Header(...)):
    headers = {
        "Authorization": authorization,
        "Content-Type": "text/event-stream",
    }

    payload = await request.json()
    print(payload)

    if 'model' not in payload:
        raise HTTPException(status_code=400, detail="Model parameter is required")
    
    if 'messages' not in payload:
        raise HTTPException(status_code=400, detail="Messages parameter is required")

    stream = payload.get("stream", False)

    payload = {
        'model': payload['model'],
        'messages': payload['messages'],
        'max_tokens': payload.get('max_tokens', 4000),
        'temperature': payload.get('temperature', 0.7),
        'top_p': payload.get('top_p', 1),
        'stream': stream
    }

    if stream:
        async def stream_generator():
            async with httpx.AsyncClient(timeout=None) as client:
                try:
                    async with client.stream("POST", UPSTREAM_API_URL, headers=headers, json=payload) as response:
                        if response.status_code != 201 and response.status_code != 200:
                            error_detail = await response.aread()
                            yield f"data: {json.dumps({'error': error_detail.decode('utf-8')})}\n\n"
                            return
                        async for chunk in response.aiter_lines():
                            print(chunk)
                            yield f"{chunk}\n" 
                except httpx.RequestError as exc:
                    yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    else:
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                response = await client.post(UPSTREAM_API_URL, headers=headers, json=payload)
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=response.text,
                    )
                return JSONResponse(content=response.json(), status_code=response.status_code)
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error communicating with the upstream API: {str(exc)}",
                )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
