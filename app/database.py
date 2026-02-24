import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base
from itsdangerous import URLSafeSerializer, BadData

# SQLite Database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./indic_scribe.db"

# Create Database Engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Token encryption/signing setup
# Using GOOGLE_CLIENT_SECRET as the encryption key
TOKEN_ENCRYPTION_KEY = os.getenv("GOOGLE_CLIENT_SECRET", "fallback_secret_key")
token_serializer = URLSafeSerializer(TOKEN_ENCRYPTION_KEY)

# SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# --- Models ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)
    email = Column(String)
    name = Column(String)
    picture = Column(String)  # Stores the URL
    access_token = Column(String, nullable=True)  # Encrypted OAuth access token
    refresh_token = Column(String, nullable=True)  # Encrypted OAuth refresh token
    ocr_credits = Column(Integer, default=10)
    voice_credits_seconds = Column(Integer, default=120)
    first_project_created = Column(Integer, default=0)  # 0 = false, 1 = true

# Create all tables (if they don't exist yet)
Base.metadata.create_all(bind=engine)

# --- Helper Functions ---
def encrypt_token(token: str) -> str:
    """
    Encrypt a token using URLSafeSerializer.
    Security Note: Tokens are encrypted at rest. Ensure GOOGLE_CLIENT_SECRET is kept secure.
    """
    try:
        return token_serializer.dumps(token)
    except Exception as e:
        raise ValueError(f"Failed to encrypt token: {e}")

def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a previously encrypted token.
    """
    try:
        return token_serializer.loads(encrypted_token)
    except BadData as e:
        raise ValueError(f"Failed to decrypt token: {e}")

def get_or_create_user(db, user_info: dict, tokens: dict = None):
    """
    Check if a user exists by google_id.
    If yes, update tokens and return the user.
    If no, create a new user with default free credits and save to DB.
    
    Args:
        db: Database session
        user_info: User information from Google OAuth
        tokens: Optional dict containing 'access_token' and 'refresh_token'
    """
    google_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    user = db.query(User).filter(User.google_id == google_id).first()
    
    if not user:
        # Create new user
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture,
            ocr_credits=10,
            voice_credits_seconds=120,
            first_project_created=0
        )
    
    # Store or update tokens if provided
    if tokens:
        if tokens.get('access_token'):
            user.access_token = encrypt_token(tokens['access_token'])
        if tokens.get('refresh_token'):
            user.refresh_token = encrypt_token(tokens['refresh_token'])
    
    db.add(user)
    db.commit()
    db.refresh(user)
        
    return user

def get_db():
    """Dependency to get the database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
