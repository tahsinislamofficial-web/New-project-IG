"""
Database models and management for IG Reel Automation Tool.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class APIKey(Base):
    """API key storage with encryption."""
    __tablename__ = 'api_keys'

    id = Column(Integer, primary_key=True)
    service_name = Column(String(50), unique=True, nullable=False)
    encrypted_key = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InstagramAccount(Base):
    """Instagram account management."""
    __tablename__ = 'instagram_accounts'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    encrypted_access_token = Column(Text, nullable=False)
    account_type = Column(String(20), default='personal')  # personal, business, creator
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)

    # Relationships
    reels = relationship("Reel", back_populates="instagram_account")

class ReelTemplate(Base):
    """Reel content templates."""
    __tablename__ = 'reel_templates'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    style = Column(String(50), nullable=False)  # truck-girl, car-girl, etc.
    description = Column(Text)
    image_prompt_template = Column(Text, nullable=False)
    motion_prompt_template = Column(Text, nullable=False)
    caption_templates = Column(JSON)  # List of caption variations
    hashtags = Column(JSON)  # List of hashtags
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Reel(Base):
    """Generated reel metadata."""
    __tablename__ = 'reels'

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    description = Column(Text)
    style = Column(String(50))
    status = Column(String(20), default='pending')  # pending, generating, completed, failed, posted
    video_model = Column(String(50))  # kling-3.0, etc.
    local_video_path = Column(String(500))
    thumbnail_path = Column(String(500))
    duration = Column(Float)  # seconds
    file_size = Column(Integer)  # bytes
    captions = Column(JSON)
    hashtags = Column(JSON)
    engagement_score = Column(Float, default=0.0)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)

    # Foreign keys
    template_id = Column(Integer, ForeignKey('reel_templates.id'))
    instagram_account_id = Column(Integer, ForeignKey('instagram_accounts.id'))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    generated_at = Column(DateTime)
    posted_at = Column(DateTime)

    # Relationships
    template = relationship("ReelTemplate")
    instagram_account = relationship("InstagramAccount", back_populates="reels")

class ScheduledPost(Base):
    """Scheduled reel posts."""
    __tablename__ = 'scheduled_posts'

    id = Column(Integer, primary_key=True)
    reel_id = Column(Integer, ForeignKey('reels.id'), nullable=False)
    instagram_account_id = Column(Integer, ForeignKey('instagram_accounts.id'), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String(20), default='scheduled')  # scheduled, posted, failed, cancelled
    post_caption = Column(Text)
    location_tag = Column(String(100)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    posted_at = Column(DateTime)

class ABTest(Base):
    """A/B testing for captions and content."""
    __tablename__ = 'ab_tests'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    test_type = Column(String(20), nullable=False)  # caption, timing, style
    status = Column(String(20), default='active')  # active, completed, paused
    variants = Column(JSON)  # List of test variants
    results = Column(JSON)  # Test results data
    winner_variant = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class AnalyticsData(Base):
    """Analytics and performance data."""
    __tablename__ = 'analytics_data'

    id = Column(Integer, primary_key=True)
    reel_id = Column(Integer, ForeignKey('reels.id'))
    instagram_account_id = Column(Integer, ForeignKey('instagram_accounts.id'))
    metric_type = Column(String(50))  # views, likes, comments, shares, reach, impressions
    value = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class User(Base):
    """User management for team collaboration."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    role = Column(String(20), default='user')  # admin, manager, creator, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

class DatabaseManager:
    """Database manager with encryption support."""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.encryption_key = None
        self.cipher = None

    def initialize(self):
        """Initialize database connection and encryption."""
        database_url = os.getenv('DATABASE_URL', 'sqlite:///reel_automation.db')
        encryption_key = os.getenv('DATABASE_ENCRYPTION_KEY')

        if not encryption_key:
            raise ValueError("DATABASE_ENCRYPTION_KEY environment variable is required")

        # Setup encryption
        self.encryption_key = encryption_key.encode()
        if len(self.encryption_key) != 32:
            # Pad or truncate to 32 bytes
            if len(self.encryption_key) < 32:
                self.encryption_key += b'\0' * (32 - len(self.encryption_key))
            else:
                self.encryption_key = self.encryption_key[:32]

        self.cipher = Fernet(self.encryption_key)

        # Create engine
        self.engine = create_engine(database_url, echo=False)

        # Create tables
        Base.metadata.create_all(bind=self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

    # API Key management
    def store_api_key(self, service_name: str, api_key: str):
        """Store encrypted API key."""
        session = self.get_session()
        try:
            encrypted_key = self.encrypt_data(api_key)
            api_key_obj = session.query(APIKey).filter_by(service_name=service_name).first()

            if api_key_obj:
                api_key_obj.encrypted_key = encrypted_key
                api_key_obj.updated_at = datetime.utcnow()
            else:
                api_key_obj = APIKey(service_name=service_name, encrypted_key=encrypted_key)
                session.add(api_key_obj)

            session.commit()
        finally:
            session.close()

    def get_api_key(self, service_name: str) -> Optional[str]:
        """Retrieve decrypted API key."""
        session = self.get_session()
        try:
            api_key_obj = session.query(APIKey).filter_by(service_name=service_name).first()
            if api_key_obj:
                return self.decrypt_data(api_key_obj.encrypted_key)
            return None
        finally:
            session.close()

    # Instagram account management
    def add_instagram_account(self, username: str, access_token: str, account_type: str = 'personal'):
        """Add Instagram account with encrypted token."""
        session = self.get_session()
        try:
            encrypted_token = self.encrypt_data(access_token)
            account = InstagramAccount(
                username=username,
                encrypted_access_token=encrypted_token,
                account_type=account_type
            )
            session.add(account)
            session.commit()
            return account.id
        finally:
            session.close()

    def get_instagram_accounts(self) -> List[Dict]:
        """Get all Instagram accounts."""
        session = self.get_session()
        try:
            accounts = session.query(InstagramAccount).filter_by(is_active=True).all()
            result = []
            for account in accounts:
                result.append({
                    'id': account.id,
                    'username': account.username,
                    'account_type': account.account_type,
                    'last_used': account.last_used
                })
            return result
        finally:
            session.close()

    # Reel template management
    def create_reel_template(self, name: str, style: str, image_prompt: str,
                           motion_prompt: str, captions: List[str], hashtags: List[str]):
        """Create a new reel template."""
        session = self.get_session()
        try:
            template = ReelTemplate(
                name=name,
                style=style,
                image_prompt_template=image_prompt,
                motion_prompt_template=motion_prompt,
                caption_templates=captions,
                hashtags=hashtags
            )
            session.add(template)
            session.commit()
            return template.id
        finally:
            session.close()

    def get_reel_templates(self, style: Optional[str] = None) -> List[Dict]:
        """Get reel templates, optionally filtered by style."""
        session = self.get_session()
        try:
            query = session.query(ReelTemplate).filter_by(is_active=True)
            if style:
                query = query.filter_by(style=style)

            templates = query.all()
            result = []
            for template in templates:
                result.append({
                    'id': template.id,
                    'name': template.name,
                    'style': template.style,
                    'description': template.description,
                    'captions': template.caption_templates,
                    'hashtags': template.hashtags
                })
            return result
        finally:
            session.close()

    # Reel management
    def create_reel(self, title: str, style: str, template_id: Optional[int] = None,
                   instagram_account_id: Optional[int] = None) -> int:
        """Create a new reel record."""
        session = self.get_session()
        try:
            reel = Reel(
                title=title,
                style=style,
                template_id=template_id,
                instagram_account_id=instagram_account_id
            )
            session.add(reel)
            session.commit()
            return reel.id
        finally:
            session.close()

    def update_reel_status(self, reel_id: int, status: str, **kwargs):
        """Update reel status and metadata."""
        session = self.get_session()
        try:
            reel = session.query(Reel).filter_by(id=reel_id).first()
            if reel:
                reel.status = status
                for key, value in kwargs.items():
                    if hasattr(reel, key):
                        setattr(reel, key, value)
                session.commit()
        finally:
            session.close()

    def get_reels(self, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get reels with optional status filter."""
        session = self.get_session()
        try:
            query = session.query(Reel).order_by(Reel.created_at.desc())
            if status:
                query = query.filter_by(status=status)
            query = query.limit(limit)

            reels = query.all()
            result = []
            for reel in reels:
                result.append({
                    'id': reel.id,
                    'title': reel.title,
                    'style': reel.style,
                    'status': reel.status,
                    'created_at': reel.created_at,
                    'posted_at': reel.posted_at,
                    'engagement_score': reel.engagement_score
                })
            return result
        finally:
            session.close()

    # Scheduled posts management
    def schedule_post(self, reel_id: int, instagram_account_id: int,
                     scheduled_time: datetime, caption: str = "") -> int:
        """Schedule a reel post."""
        session = self.get_session()
        try:
            scheduled_post = ScheduledPost(
                reel_id=reel_id,
                instagram_account_id=instagram_account_id,
                scheduled_time=scheduled_time,
                post_caption=caption
            )
            session.add(scheduled_post)
            session.commit()
            return scheduled_post.id
        finally:
            session.close()

    def get_scheduled_posts(self, upcoming_only: bool = True) -> List[Dict]:
        """Get scheduled posts."""
        session = self.get_session()
        try:
            query = session.query(ScheduledPost).filter_by(status='scheduled')
            if upcoming_only:
                query = query.filter(ScheduledPost.scheduled_time > datetime.utcnow())

            posts = query.order_by(ScheduledPost.scheduled_time).all()
            result = []
            for post in posts:
                result.append({
                    'id': post.id,
                    'reel_id': post.reel_id,
                    'instagram_account_id': post.instagram_account_id,
                    'scheduled_time': post.scheduled_time,
                    'caption': post.post_caption
                })
            return result
        finally:
            session.close()

    # Analytics
    def store_analytics(self, reel_id: int, instagram_account_id: int,
                       metric_type: str, value: float):
        """Store analytics data."""
        session = self.get_session()
        try:
            analytics = AnalyticsData(
                reel_id=reel_id,
                instagram_account_id=instagram_account_id,
                metric_type=metric_type,
                value=value
            )
            session.add(analytics)
            session.commit()
        finally:
            session.close()

    def get_analytics_summary(self, days: int = 30) -> Dict:
        """Get analytics summary for the last N days."""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Aggregate metrics
            metrics = session.query(
                AnalyticsData.metric_type,
                session.query(AnalyticsData.value).filter(
                    AnalyticsData.metric_type == AnalyticsData.metric_type,
                    AnalyticsData.timestamp >= cutoff_date
                ).label('total_value')
            ).group_by(AnalyticsData.metric_type).all()

            result = {}
            for metric_type, total_value in metrics:
                result[metric_type] = total_value

            return result
        finally:
            session.close()