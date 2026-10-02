import db

import random


adjectives = [
    "Blue", "Fast", "Silent", "Happy", "Cool",
    "Brave", "Swift", "Lucky", "Clever", "Wild",
    "Bright", "Calm", "Fierce", "Gentle", "Mighty",
    "Rapid", "Smart", "Bold", "Fresh", "Cosmic",
    "Golden", "Silver", "Tiny", "Big", "Magic",
    "Shadow", "Sunny", "Stormy", "Flying", "Frozen"
]

animals = [
    "Panda", "Fox", "Tiger", "Wolf", "Eagle",
    "Bear", "Lion", "Rabbit", "Falcon", "Deer",
    "Otter", "Koala", "Penguin", "Dolphin", "Hawk",
    "Cheetah", "Leopard", "Monkey", "Parrot", "Owl",
    "Horse", "Zebra", "Giraffe", "Elephant", "Turtle",
    "Swan", "Rabbit", "Badger", "Raccoon", "Squirrel"
]

def random_user_name(room_id):

    while True:

        name = (
            random.choice(adjectives)
            + random.choice(animals)
        )

        exists = db.user_collection.find_one({
            "room_id": room_id,
            "user_name": name
        })

        if exists is None:
            return name

def random_session_token():
    import secrets
    return secrets.token_urlsafe(32)
