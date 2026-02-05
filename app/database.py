from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager with cloud optimization"""
    
    client: AsyncIOMotorClient = None
    
    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB with optimized settings for cloud deployment"""
        try:
            cls.client = AsyncIOMotorClient(
                settings.mongodb_url,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size,
                maxIdleTimeMS=settings.mongodb_max_idle_time_ms,
                connectTimeoutMS=settings.mongodb_connect_timeout_ms,
                serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
                retryWrites=True,
                retryReads=True,
                w='majority',
                # Compression for faster network transfer
                compressors='snappy,zlib',
            )
            # Verify connection
            await cls.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB (Cloud Optimized)")
            logger.info(f"Pool size: {settings.mongodb_min_pool_size}-{settings.mongodb_max_pool_size}")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            logger.info("MongoDB connection closed")
    
    @classmethod
    def get_database(cls):
        """Get database instance"""
        if cls.client is None:
            raise Exception("Database not connected. Call connect_db() first.")
        return cls.client[settings.mongodb_db_name]
    
    @classmethod
    def get_sessions_collection(cls):
        """Get sessions collection"""
        db = cls.get_database()
        return db.sessions
    
    @classmethod
    def get_intelligence_collection(cls):
        """Get intelligence collection"""
        db = cls.get_database()
        return db.intelligence
    
    @classmethod
    def get_callbacks_collection(cls):
        """Get callbacks collection"""
        db = cls.get_database()
        return db.callbacks


# Convenience function
def get_db():
    """Dependency for getting database"""
    return Database.get_database()


async def init_indexes():
    """Initialize database indexes for optimal performance"""
    try:
        sessions_collection = Database.get_sessions_collection()
        
        # Create indexes
        await sessions_collection.create_index("sessionId", unique=True)
        await sessions_collection.create_index("startTime")
        await sessions_collection.create_index("status")
        await sessions_collection.create_index([("scamDetected", 1), ("status", 1)])
        
        # Training examples indexes
        training_collection = Database.get_database().training_examples
        await training_collection.create_index("scam_type")
        await training_collection.create_index("source")
        await training_collection.create_index("created_at")
        
        # Callback response indexes
        callbacks_collection = Database.get_callbacks_collection()
        await callbacks_collection.create_index("sessionId")
        await callbacks_collection.create_index("sentTime")
        await callbacks_collection.create_index("success")
        await callbacks_collection.create_index([("sessionId", 1), ("sentTime", -1)])
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
