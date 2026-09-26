from pymongo import MongoClient
client=MongoClient("mongodb://localhost:27017/")


db=client["quick_share_db"]
user_collection=db["room_users"]
rooms_collection=db["rooms"]
messages_collection=db["messages"]
files_collection = db["files"]

