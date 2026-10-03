from pymongo import MongoClient
client = MongoClient(
    "mongodb+srv://aniketjaiswal669_db_user:QuickShare12345@quickshare.9a6n0cv.mongodb.net/quick_share_db?appName=QuickShare"
)



db=client["quick_share_db"]
user_collection=db["room_users"]
rooms_collection=db["rooms"]
messages_collection=db["messages"]
files_collection = db["files"]

