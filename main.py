from fastapi import FastAPI, UploadFile, Form, File, Query, Path
from Quick_share_backend import data_models, router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/room")
def room(room_data: data_models.room):
    return router.room(
        room_data.room_id,
        room_data.action
    )


@app.post("/upload")
async def upload_file(
    room_id: str = Form(..., min_length=4, max_length=15),
    session_token: str = Form(..., min_length=1),
    filename: str = Form(..., min_length=1, max_length=255),
    content_type: str = Form(..., min_length=1),
    file_data: str = Form(..., min_length=1)
):
    return await router.upload_file(
        room_id,
        session_token,
        filename,
        content_type,
        file_data
    )


@app.get("/history/{room_id}")
def get_messages(
    room_id: str = Path(..., min_length=6, max_length=15),
    session_token: str = Query(..., min_length=1)
):
    return router.get_messages(
        room_id,
        session_token
    )


@app.post("/room/out")
def out(
    room_id: str = Query(..., min_length=6, max_length=15),
    session_token: str = Query(..., min_length=1)
):
    return router.room_out(
        room_id,
        session_token
    )


@app.get("/file/{file_id}")
def get_file(
    file_id: str = Path(..., min_length=1),
    session_token: str = Query(..., min_length=1)
):
    return router.get_file(
        file_id,
        session_token
    )


@app.delete("/message/{message_id}")
async def delete_message_route(
    message_id: str,
    session_token: str
):
    return await router.delete_message(
        message_id,
        session_token
    )

@app.get("/download/{file_id}")
async def download_file(
    file_id: str,
    session_token: str = Query(...)
):
    return router.download_file(
        file_id=file_id,
        session_token=session_token
    )
