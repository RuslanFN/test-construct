import asyncio
from dotenv import load_dotenv
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
load_dotenv()
mongo_host = os.getenv('mongo_host')
mongo_port = os.getenv('mongo_port')
mongo_username = os.getenv('mongo_username')
mongo_password = os.getenv('mongo_password')
mongo_db_name = os.getenv('mongo_db_name')
mongo_uri = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db_name}"   
async def connect_to_mongo():
    try:
        client = AsyncIOMotorClient(mongo_uri, serverselectiontimeoutms=5000)
        await client.admin.command('ping')
        bases = await client.list_databases()
        print("Connected to MongoDB successfully!", "Databases:",  [base for base in await bases.to_list(length=100)])
        return client
    except ServerSelectionTimeoutError as e:
        print("Failed to connect to MongoDB, error:", e)
        return None

if __name__ == "__main__":
    asyncio.run(connect_to_mongo())