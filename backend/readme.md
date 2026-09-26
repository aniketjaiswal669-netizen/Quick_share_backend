# Quick Share Backend

Backend for **Quick Share**, a real-time room-based file and messaging application built with **FastAPI, MongoDB, REST APIs, and WebSockets**.

Users can create or join rooms, exchange real-time messages, send files, view active users, retrieve chat history, and delete messages according to their permissions.

---

## 🚀 Features

* Create and join chat rooms
* Session-token based authentication
* Random username generation for users
* Real-time messaging using WebSockets
* Active-user tracking
* File upload using Base64 data
* File storage directly in MongoDB
* File download/open API
* Chat history
* Message deletion
* Admin and normal-user permissions
* Room exit and room termination
* Automatic cleanup of room-related data

---

## 🛠️ Tech Stack

### Backend

* **Python**
* **FastAPI**
* **Uvicorn**
* **MongoDB**
* **PyMongo**
* **WebSockets**
* **Pydantic**

### Database

MongoDB is used to store:

* Rooms
* Users
* Messages
* Files

---

## 📁 Project Structure

```text
Quick_share/
│
├── backend/
│   ├── main.py
│   ├── db.py
│   ├── data_models.py
│   ├── router.py
│   └── websocket.py
│
├── venv/
│
└── README.md
```

### File Responsibilities

| File             | Purpose                            |
| ---------------- | ---------------------------------- |
| `main.py`        | FastAPI application and API routes |
| `db.py`          | MongoDB connection and collections |
| `data_models.py` | Pydantic request/response models   |
| `router.py`      | Backend business logic             |
| `websocket.py`   | Real-time WebSocket communication  |

---

# 🗄️ Database Structure

Database:

```text
quick_share_db
```

Collections:

```text
rooms
room_users
messages
files
```

### `rooms`

Stores room information.

Example:

```json
{
  "room_id": "UIU888",
  "created_at": "..."
}
```

### `room_users`

Stores users belonging to rooms.

Example:

```json
{
  "room_id": "UIU888",
  "user_name": "LuckyLeopard",
  "user_type": "admin",
  "session_token": "...",
  "joined_at": "..."
}
```

### `messages`

Stores chat messages and references to uploaded files.

Example:

```json
{
  "room_id": "UIU888",
  "user_name": "LuckyLeopard",
  "message": "Hello",
  "file_id": null,
  "sent_at": "..."
}
```

For a file message:

```json
{
  "room_id": "UIU888",
  "user_name": "LuckyLeopard",
  "message": null,
  "file_id": "...",
  "sent_at": "..."
}
```

### `files`

Files are stored directly in MongoDB.

Example:

```json
{
  "room_id": "UIU888",
  "user_name": "LuckyLeopard",
  "filename": "image.png",
  "content_type": "image/png",
  "size": 123456,
  "file_data": "<binary data>",
  "created_at": "..."
}
```

> **Note:** This project does not use MongoDB GridFS. File data is stored directly in the `files` collection.

---

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone https://github.com/aniketjaiswal669-netizen/Quick_Share.git
cd Quick_Share
```

Switch to the backend branch if required:

```bash
git checkout develop
```

---

## 2. Create a virtual environment

```bash
python3 -m venv venv
```

Activate it:

### Linux/macOS

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not present, install the main dependencies:

```bash
pip install fastapi uvicorn pymongo websockets pydantic
```

---

# 🔐 MongoDB Configuration

The backend requires a MongoDB database.

Configure the MongoDB connection in:

```text
backend/db.py
```

The application uses:

```text
quick_share_db
```

Example structure:

```python
from pymongo import MongoClient

client = MongoClient("YOUR_MONGODB_CONNECTION_STRING")

db = client["quick_share_db"]

rooms_collection = db["rooms"]
user_collection = db["room_users"]
messages_collection = db["messages"]
files_collection = db["files"]
```

For production, use an environment variable instead of placing credentials directly in source code.

---

# ▶️ Running the Backend

From the project root:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The REST API will be available at:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

---

# 🔌 WebSocket Server

Quick Share also uses WebSockets for real-time communication.

Example:

```text
ws://YOUR_IP:8001?session_token=SESSION_TOKEN
```

Example on a local network:

```text
ws://192.168.1.120:8001?session_token=SESSION_TOKEN
```

The WebSocket connection authenticates the user using the `session_token`.

---

# 🔑 Authentication

Quick Share uses a **session token** to identify users.

When a user creates or joins a room, the backend returns:

```json
{
  "room_id": "UIU888",
  "session_token": "SESSION_TOKEN",
  "user_name": "LuckyLeopard"
}
```

The frontend must keep the session token and send it with protected requests.

---

# 📡 REST API

## 1. Create / Join Room

### Endpoint

```http
POST /room
```

### Request

```json
{
  "room_id": "UIU888",
  "action": "create"
}
```

For joining:

```json
{
  "room_id": "UIU888",
  "action": "join"
}
```

### Response

```json
{
  "room_id": "UIU888",
  "session_token": "...",
  "user_name": "LuckyLeopard"
}
```

---

# 🚪 Exit / End Room

### Endpoint

```http
POST /room/out
```

The session token is used to identify the current user.

### Normal User

A normal user leaving the room removes their user record.

### Admin

The admin can end the room and clean up associated room data.

Cleanup includes:

```text
rooms
room_users
messages
files
```

---

# 📤 Upload File

### Endpoint

```http
POST /upload
```

The frontend sends:

```text
room_id
session_token
filename
content_type
file_data
```

`file_data` is sent as a Base64 encoded string.

### Example

```text
room_id = UIU888
session_token = ...
filename = photo.png
content_type = image/png
file_data = BASE64_DATA
```

### Response

```json
{
  "message": "File uploaded successfully",
  "file_id": "...",
  "filename": "photo.png",
  "content_type": "image/png",
  "size": 123456
}
```

The returned `file_id` is then sent through the WebSocket message.

---

# 📥 Get / Open File

The file API uses the `file_id` to retrieve a stored file.

The backend:

1. Validates the session token.
2. Finds the requested file.
3. Verifies that the file belongs to the user's room.
4. Returns the stored file data with the correct content type.

This allows the frontend to display images and open/download other supported files.

---

# 💬 WebSocket Messaging

After connecting:

```text
ws://YOUR_IP:8001?session_token=SESSION_TOKEN
```

the client can send messages through the WebSocket.

A text message can contain:

```json
{
  "message": "Hello everyone"
}
```

A file message can contain:

```json
{
  "message": null,
  "file_id": "FILE_ID"
}
```

The server broadcasts messages to users connected to the same room.

### Example server response

```json
{
  "type": "message",
  "data": {
    "room_id": "UIU888",
    "user_name": "LuckyLeopard",
    "message": "Hello everyone",
    "file_id": null,
    "type": "text",
    "created_at": "...",
    "_id": "..."
  }
}
```

---

# 👥 Active Users

The backend maintains currently connected WebSocket users.

The active-user API returns information such as:

```json
{
  "room_id": "UIU888",
  "active_users": [
    {
      "user_name": "LuckyLeopard",
      "user_type": "admin",
      "joined_at": "..."
    },
    {
      "user_name": "GoldenOtter",
      "user_type": "user",
      "joined_at": "..."
    }
  ],
  "count": 2
}
```

The WebSocket connection is responsible for detecting users connecting and disconnecting in real time.

---

# 🕘 Chat History

### Endpoint

```http
GET /history/{room_id}
```

The request requires a valid session token.

Example:

```text
GET /history/UIU888?session_token=SESSION_TOKEN
```

History contains:

```text
_id
room_id
user_name
message
file_id
sent_at
```

The frontend can use `file_id` to retrieve previously uploaded files.

---

# 🗑️ Delete Message

The backend supports message deletion.

The server verifies:

1. The message exists.
2. The session token is valid.
3. The message belongs to the user's room.
4. The user has permission to delete the message.

### Permissions

```text
Admin
 └── Can delete messages from users

Normal User
 └── Can delete their own messages
```

---

# 🔄 Application Flow

```text
                    ┌─────────────────┐
                    │     Frontend    │
                    │   Expo / React  │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
        ┌──────────────┐          ┌──────────────┐
        │ REST APIs    │          │  WebSocket   │
        │ Port 8000    │          │  Port 8001   │
        └──────┬───────┘          └──────┬───────┘
               │                         │
               └────────────┬────────────┘
                            ▼
                    ┌───────────────┐
                    │    FastAPI    │
                    │    Backend    │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    MongoDB    │
                    │ quick_share_db│
                    └───────────────┘
```

---

# 📁 File Sending Flow

```text
Frontend
   │
   │ Base64 file data
   ▼
POST /upload
   │
   ▼
Backend validates session
   │
   ▼
Store file in MongoDB
   │
   ▼
Return file_id
   │
   ▼
Frontend sends file_id
through WebSocket
   │
   ▼
Backend broadcasts message
   │
   ▼
Other users receive file_id
   │
   ▼
Frontend requests file
   │
   ▼
File displayed / opened
```

---

# 🔒 Security

The backend uses session tokens to protect room-specific operations.

Protected operations include:

* File upload
* File retrieval
* Chat history
* Message deletion
* Active-user information
* Room exit

The backend should verify that a requested file or message belongs to the authenticated user's room before returning or modifying it.

For production deployment, additional security should be considered:

* HTTPS / WSS
* Secure environment variables
* File-size limits
* MIME-type validation
* Rate limiting
* Strong session-token generation
* MongoDB authentication
* Input validation

---

# 🧪 API Documentation

FastAPI automatically provides interactive API documentation.

Open:

```text
http://localhost:8000/docs
```

Alternative documentation:

```text
http://localhost:8000/redoc
```

---

# 🌐 Frontend Connection

For a frontend running on the same local network, configure the backend IP.

Example:

```text
REST API:
http://192.168.1.120:8000

WebSocket:
ws://192.168.1.120:8001
```

The IP address depends on the machine running the backend.

---

# 🐛 Troubleshooting

## `ModuleNotFoundError`

If running:

```bash
uvicorn main:app
```

from the project root causes import errors, run:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Or enter the backend directory:

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## WebSocket Not Connecting

Check:

```text
1. Backend WebSocket server is running
2. Correct IP address is being used
3. Port 8001 is accessible
4. session_token is valid
5. Phone and computer are on the same network
```

---

## MongoDB Connection Error

Check:

```text
MongoDB connection string
MongoDB server status
Database permissions
Network access / IP whitelist
```

---

# 📌 Development Notes

Quick Share currently uses:

```text
FastAPI       → REST backend
WebSocket     → Real-time communication
MongoDB       → Persistent storage
Base64        → File transfer from frontend
```

GridFS is **not used**.

Files are stored directly inside the MongoDB `files` collection.

---

# 🚧 Future Improvements

Potential improvements include:

* Better file-size management
* File compression
* Message reactions
* Typing indicators
* Read receipts
* Admin handover when the admin leaves
* Better WebSocket connection recovery
* Redis for scalable WebSocket state
* Cloud object storage for large files
* Production authentication
* HTTPS/WSS deployment
* A
