from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship, validates
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=True, index=True)
    hashed_password = Column(String, nullable=False)
    phone = Column(String, nullable=True, index=True)
    village = Column(String, nullable=True)
    region = Column(String, nullable=True, index=True)
    total_surface = Column(Float, default=0.0)
    
    # Role-based access control (RBAC)
    role = Column(String, default="farmer", index=True)  # admin, farmer, client, bank, insurance
    account_type = Column(String, default="farmer")
    is_admin = Column(Boolean, default=False, index=True)  # Backward compatibility
    is_validated = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    
    # Multi-Factor Authentication (MFA)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String, nullable=True)  # Base32-encoded TOTP secret
    mfa_backup_codes = Column(String, nullable=True)  # Comma-separated backup codes
    
    # Security tracking
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    crops = relationship("Crop", back_populates="owner", cascade="all, delete-orphan")
    fields = relationship("Field", back_populates="owner", cascade="all, delete-orphan")
    finance_records = relationship("FinanceRecord", back_populates="owner", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="owner", cascade="all, delete-orphan")
    insurances = relationship("Insurance", back_populates="owner", cascade="all, delete-orphan")
    blockchain_traces = relationship("BlockchainTrace", back_populates="user", cascade="all, delete-orphan")
    community_tokens = relationship("CommunityToken", back_populates="user", cascade="all, delete-orphan")
    marketplace_transactions = relationship("MarketplaceTransaction", back_populates="seller", cascade="all, delete-orphan", foreign_keys="MarketplaceTransaction.seller_id")
    social_posts = relationship("SocialPost", back_populates="author", cascade="all, delete-orphan")
    social_comments = relationship("SocialComment", back_populates="author", cascade="all, delete-orphan")
    social_groups = relationship("SocialGroup", back_populates="creator", cascade="all, delete-orphan")
    social_group_memberships = relationship("SocialGroupMember", back_populates="user", cascade="all, delete-orphan")
    courses_created = relationship("LearningCourse", back_populates="creator", cascade="all, delete-orphan")
    webinars_created = relationship("Webinar", back_populates="creator", cascade="all, delete-orphan")
    webinar_registrations = relationship("WebinarRegistration", back_populates="user", cascade="all, delete-orphan")
    cooperative_trainings = relationship("CooperativeTraining", back_populates="organizer", cascade="all, delete-orphan")
    training_participations = relationship("TrainingParticipant", back_populates="user", cascade="all, delete-orphan")
    cooperatives = relationship("Cooperative", back_populates="founder", cascade="all, delete-orphan")
    cooperative_memberships = relationship("CooperativeMember", back_populates="user", cascade="all, delete-orphan")
    cooperative_contributions = relationship("CooperativeContribution", back_populates="user", cascade="all, delete-orphan")
    resource_exchanges = relationship(
        "ResourceExchange",
        back_populates="requester",
        cascade="all, delete-orphan",
        foreign_keys="ResourceExchange.requester_id",
    )
    recycling_records = relationship("RecyclingRecord", back_populates="user", cascade="all, delete-orphan")
    social_post_likes = relationship("SocialPostLike", back_populates="user", cascade="all, delete-orphan")
    learning_enrollments = relationship("LearningEnrollment", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    @validates("role")
    def _set_role_compatibility(self, key, value):
        normalized = (value or "farmer").strip().lower()
        allowed = {"admin", "farmer", "client", "bank", "insurance"}
        if normalized not in allowed:
            normalized = "farmer"
        self.account_type = normalized
        self.is_admin = normalized == "admin"
        return normalized

    @property
    def effective_role(self):
        """Canonical role used for RBAC. Backward compatibility falls back to account_type and is_admin."""
        if self.role and self.role.strip():
            normalized = self.role.strip().lower()
            if normalized in {"admin", "farmer", "client", "bank", "insurance"}:
                return normalized
        if self.account_type and self.account_type.strip():
            normalized = self.account_type.strip().lower()
            if normalized in {"admin", "farmer", "client", "bank", "insurance"}:
                return normalized
        if self.is_admin:
            return "admin"
        return "farmer"

class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    surface = Column(Float, default=0.0)
    planting_date = Column(DateTime, default=datetime.datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="crops")

class Field(Base):
    __tablename__ = "fields"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    area_ha = Column(Float, default=0.0)
    crop_rotation = Column(String, nullable=True)
    soil_type = Column(String, nullable=True)
    irrigation_system = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    satellite_texture = Column(String, nullable=True)
    boundary_points = Column(JSON, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="fields")

class FinanceRecord(Base):
    __tablename__ = "finance_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    revenue = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="finance_records")

class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected
    requested_date = Column(DateTime, default=datetime.datetime.utcnow)
    approved_date = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="loans")

class Insurance(Base):
    __tablename__ = "insurances"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # e.g., "crop", "equipment"
    premium = Column(Float, nullable=False)
    coverage = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected
    requested_date = Column(DateTime, default=datetime.datetime.utcnow)
    approved_date = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="insurances")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, nullable=False, unique=True, index=True)
    token_hash = Column(String, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class TokenRevocation(Base):
    __tablename__ = "token_revocations"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, nullable=False, unique=True, index=True)
    token_type = Column(String, nullable=False, index=True)
    revoked_at = Column(DateTime, default=datetime.datetime.utcnow)
    reason = Column(String, nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, nullable=False, index=True, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="password_reset_tokens")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event = Column(String, nullable=False)
    detail = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


class PaymentIdempotency(Base):
    __tablename__ = "payment_idempotency"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, nullable=True)  # processing, succeeded, failed
    result_json = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sensor_type = Column(String, nullable=False, index=True)  # e.g., "pump_vibration", "battery_level", "water_flow", "soil_moisture", "temperature", "humidity", "light", "ph_level"
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)  # e.g., "Hz", "%", "L/min", "%", "°C", "lux", "pH"
    location = Column(String, nullable=True)  # GPS coordinates or field name
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=True)  # Link to specific crop
    device_id = Column(String, nullable=True, index=True)  # IoT device identifier
    metadata_json = Column("metadata", String, nullable=True)  # JSON string for additional sensor data
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User")
    crop = relationship("Crop")


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, nullable=False)  # City/region name
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    temperature = Column(Float, nullable=True)  # °C
    humidity = Column(Float, nullable=True)  # %
    precipitation = Column(Float, nullable=True)  # mm
    wind_speed = Column(Float, nullable=True)  # km/h
    wind_direction = Column(Float, nullable=True)  # degrees
    pressure = Column(Float, nullable=True)  # hPa
    uv_index = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)  # %
    forecast_data = Column(String, nullable=True)  # JSON string for forecast
    source = Column(String, default="open-meteo")  # API source
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    forecast_date = Column(DateTime, nullable=True)  # For forecast data


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    crop_type = Column(String, nullable=False)  # e.g., "maize", "rice", "millet"
    market_location = Column(String, nullable=False)  # Market name/city
    price_per_kg = Column(Float, nullable=False)  # XOF per kg
    currency = Column(String, default="XOF")
    volume_traded = Column(Float, nullable=True)  # kg
    quality_grade = Column(String, nullable=True)  # A, B, C, etc.
    source = Column(String, default="worldbank")  # Data source
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class PlantDisease(Base):
    __tablename__ = "plant_diseases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=True)
    image_path = Column(String, nullable=True)  # Path to uploaded image
    disease_name = Column(String, nullable=False)  # e.g., "leaf_spot", "powdery_mildew"
    confidence_score = Column(Float, nullable=False)  # 0-1
    severity_level = Column(String, nullable=False)  # low, medium, high, critical
    affected_area = Column(Float, nullable=True)  # % of plant affected
    treatment_recommendation = Column(String, nullable=True)  # Recommended treatment
    recommendations = Column(String, nullable=True)  # JSON encoded recommendations list
    ai_model_version = Column(String, nullable=True)  # Version of AI model used
    diagnosis_date = Column(DateTime, default=datetime.datetime.utcnow)
    follow_up_date = Column(DateTime, nullable=True)

    user = relationship("User")
    crop = relationship("Crop")


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    response = Column(String, nullable=True)
    responded_at = Column(DateTime, nullable=True)

    user = relationship("User")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)
    severity = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User")


class SatelliteObservation(Base):
    __tablename__ = "satellite_observations"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    region = Column(String, nullable=True)
    cercle = Column(String, nullable=True)
    vegetation_index = Column(Float, nullable=False)
    ndvi_source = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    advisor_note = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    # `metadata` is a reserved attribute name in SQLAlchemy's Declarative API.
    # Use `metadata_json` as the mapped attribute but keep the DB column name as
    # `metadata` for compatibility with existing data if necessary.
    metadata_json = Column("metadata", String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=True)
    recommendation_type = Column(String, nullable=False)  # irrigation, fertilization, pest_control, harvesting
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    priority_level = Column(String, default="medium")  # low, medium, high, critical
    confidence_score = Column(Float, nullable=True)  # AI confidence 0-1
    expected_impact = Column(String, nullable=True)  # Expected outcome
    implementation_cost = Column(Float, nullable=True)  # Estimated cost in XOF
    implementation_time = Column(String, nullable=True)  # Time to implement
    ai_model_version = Column(String, nullable=True)
    weather_factors = Column(String, nullable=True)  # JSON weather data used
    sensor_data = Column(String, nullable=True)  # JSON sensor data used
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    implemented_at = Column(DateTime, nullable=True)
    effectiveness_rating = Column(Float, nullable=True)  # User rating 1-5

    user = relationship("User")
    crop = relationship("Crop")


class YieldPrediction(Base):
    __tablename__ = "yield_predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=True)
    predicted_yield = Column(Float, nullable=False)  # kg/ha
    yield_unit = Column(String, default="kg/ha")
    confidence_interval_low = Column(Float, nullable=True)
    confidence_interval_high = Column(Float, nullable=True)
    prediction_date = Column(DateTime, default=datetime.datetime.utcnow)
    harvest_date = Column(DateTime, nullable=True)
    actual_yield = Column(Float, nullable=True)  # Real yield after harvest
    accuracy_score = Column(Float, nullable=True)  # Prediction accuracy
    factors_used = Column(String, nullable=True)  # JSON of factors considered
    ai_model_version = Column(String, nullable=True)

    user = relationship("User")
    crop = relationship("Crop")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, nullable=False)  # Chat session identifier
    message_type = Column(String, nullable=False)  # user, assistant
    content = Column(String, nullable=False)
    language = Column(String, default="fr")  # fr, en, bm (Bambara)
    intent_detected = Column(String, nullable=True)  # AI-detected intent
    response_generated = Column(String, nullable=True)  # AI response
    context_data = Column(String, nullable=True)  # JSON context used
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False, index=True)
    product_type = Column(String, nullable=False, index=True)
    quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    currency = Column(String, default="XOF")
    location = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    is_verified = Column(Boolean, default=False)
    quality_certified = Column(Boolean, default=False)
    organic_certified = Column(Boolean, default=False)
    blockchain_hash = Column(String, nullable=True)
    images = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    seller = relationship("User")
    orders = relationship("MarketplaceOrder", back_populates="listing", cascade="all, delete-orphan")
    reviews = relationship("MarketplaceReview", back_populates="listing", cascade="all, delete-orphan")


class MarketplaceOrder(Base):
    __tablename__ = "marketplace_orders"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    currency = Column(String, default="XOF")
    payment_method = Column(String, nullable=True)
    status = Column(String, default="pending")
    shipping_address = Column(String, nullable=True)
    recipient_name = Column(String, nullable=True)
    order_notes = Column(String, nullable=True)
    logistics_provider = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True)
    delivery_deadline = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    blockchain_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    buyer = relationship("User")
    listing = relationship("MarketplaceListing", back_populates="orders")
    reviews = relationship("MarketplaceReview", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("MarketplacePayment", back_populates="order", cascade="all, delete-orphan")


class MarketplacePayment(Base):
    __tablename__ = "marketplace_payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("marketplace_orders.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="XOF")
    payment_method = Column(String, nullable=False)  # mobile_money, cash_on_delivery, bank_transfer
    payment_provider = Column(String, nullable=True)  # Orange Money, Wave, Bank name
    transaction_id = Column(String, nullable=True)   # External transaction reference
    status = Column(String, default="pending")       # pending, completed, failed, refunded
    blockchain_tx_hash = Column(String, nullable=True)  # Simulated blockchain transaction hash
    payment_gateway_response = Column(String, nullable=True)  # Raw gateway response
    failure_reason = Column(String, nullable=True)   # Reason for failure if any
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    order = relationship("MarketplaceOrder", back_populates="payments")


class MarketplaceReview(Base):
    __tablename__ = "marketplace_reviews"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("marketplace_orders.id"), nullable=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    review_type = Column(String, nullable=False, default="product")
    is_verified_purchase = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    listing = relationship("MarketplaceListing", back_populates="reviews")
    order = relationship("MarketplaceOrder", back_populates="reviews")
    reviewer = relationship("User")


class BlockchainTrace(Base):
    __tablename__ = "blockchain_traces"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    origin = Column(String, nullable=True)
    certification_type = Column(String, nullable=True)
    product_type = Column(String, nullable=True)
    origin_info = Column(String, nullable=True)
    carbon_score = Column(Float, nullable=True)
    durability_label = Column(String, nullable=True)
    qr_code_data = Column(String, nullable=True)
    metadata_json = Column("metadata", String, nullable=True)
    verified = Column(Boolean, default=False)
    tx_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="blockchain_traces")
    nfts = relationship("AgriculturalNFT", back_populates="trace", cascade="all, delete-orphan")


class CommunityToken(Base):
    __tablename__ = "community_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)  # reward, redemption, transfer
    category = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    balance_after = Column(Float, nullable=True)
    blockchain_tx = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="community_tokens")


class MarketplaceTransaction(Base):
    __tablename__ = "marketplace_transactions"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="XOF")
    status = Column(String, default="completed")
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    seller = relationship("User", back_populates="marketplace_transactions", foreign_keys=[seller_id])
    buyer = relationship("User", foreign_keys=[buyer_id])


class Cooperative(Base):
    __tablename__ = "cooperatives"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    region = Column(String, nullable=True)
    description = Column(String, nullable=True)
    founder_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="active")
    governance_rules = Column(String, nullable=True)
    benefits = Column(String, nullable=True)
    blockchain_tx = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    founder = relationship("User", back_populates="cooperatives")
    members = relationship("CooperativeMember", back_populates="cooperative", cascade="all, delete-orphan")
    contributions = relationship("CooperativeContribution", back_populates="cooperative", cascade="all, delete-orphan")
    group_purchases = relationship("CooperativeGroupPurchase", back_populates="cooperative", cascade="all, delete-orphan")
    cooperative_trainings = relationship("CooperativeTraining", back_populates="cooperative", cascade="all, delete-orphan")


class CooperativeMember(Base):
    __tablename__ = "cooperative_members"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="member")
    status = Column(String, default="pending")
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(Integer, nullable=True)

    cooperative = relationship("Cooperative", back_populates="members")
    user = relationship("User", back_populates="cooperative_memberships")


class CooperativeContribution(Base):
    __tablename__ = "cooperative_contributions"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    contribution_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    cooperative = relationship("Cooperative", back_populates="contributions")
    user = relationship("User", back_populates="cooperative_contributions")


class CooperativeGroupPurchase(Base):
    __tablename__ = "cooperative_group_purchases"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False)
    product_name = Column(String, nullable=False)
    quantity_needed = Column(Float, nullable=False)
    budget_max = Column(Float, nullable=False)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    cooperative = relationship("Cooperative", back_populates="group_purchases")
    organizer = relationship("User")
    participants = relationship("CooperativePurchaseParticipant", back_populates="purchase", cascade="all, delete-orphan")


class CooperativePurchaseParticipant(Base):
    __tablename__ = "cooperative_purchase_participants"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("cooperative_group_purchases.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quantity_committed = Column(Float, nullable=False)
    status = Column(String, default="committed")
    committed_at = Column(DateTime, default=datetime.datetime.utcnow)

    purchase = relationship("CooperativeGroupPurchase", back_populates="participants")
    user = relationship("User")


class ResourceExchange(Base):
    __tablename__ = "resource_exchanges"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resource_type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    status = Column(String, default="open")
    exchange_partner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    requester = relationship("User", back_populates="resource_exchanges", foreign_keys=[requester_id])
    exchange_partner = relationship("User", foreign_keys=[exchange_partner_id])


class SocialPost(Base):
    __tablename__ = "social_posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("social_groups.id"), nullable=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    media_url = Column(String, nullable=True)
    experience_share = Column(Boolean, default=False)
    tags = Column(String, nullable=True)
    likes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    author = relationship("User", back_populates="social_posts")
    group = relationship("SocialGroup", back_populates="posts")
    comments = relationship("SocialComment", back_populates="post", cascade="all, delete-orphan")
    likes_records = relationship("SocialPostLike", back_populates="post", cascade="all, delete-orphan")


class SocialComment(Base):
    __tablename__ = "social_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey("social_comments.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    post = relationship("SocialPost", back_populates="comments")
    author = relationship("User", back_populates="social_comments")
    parent = relationship("SocialComment", remote_side=[id])


class SocialGroup(Base):
    __tablename__ = "social_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    privacy = Column(String, default="public")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    creator = relationship("User", back_populates="social_groups")
    members = relationship("SocialGroupMember", back_populates="group", cascade="all, delete-orphan")
    posts = relationship("SocialPost", back_populates="group", cascade="all, delete-orphan")


class SocialGroupMember(Base):
    __tablename__ = "social_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("social_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="member")
    status = Column(String, default="active")
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

    group = relationship("SocialGroup", back_populates="members")
    user = relationship("User", back_populates="social_group_memberships")


class LearningCourse(Base):
    __tablename__ = "learning_courses"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    material_url = Column(String, nullable=True)
    level = Column(String, default="beginner")
    category = Column(String, nullable=True)
    content_type = Column(String, default="course")
    published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    creator = relationship("User", back_populates="courses_created")
    enrollments = relationship("LearningEnrollment", back_populates="course", cascade="all, delete-orphan")


class SocialPostLike(Base):
    __tablename__ = "social_post_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("social_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    post = relationship("SocialPost", back_populates="likes_records")
    user = relationship("User", back_populates="social_post_likes")


class LearningEnrollment(Base):
    __tablename__ = "learning_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("learning_courses.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    progress_percent = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    enrolled_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    course = relationship("LearningCourse", back_populates="enrollments")
    user = relationship("User", back_populates="learning_enrollments")


class Webinar(Base):
    __tablename__ = "webinars"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    presenter = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    registration_link = Column(String, nullable=True)
    max_participants = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    creator = relationship("User", back_populates="webinars_created")
    registrations = relationship("WebinarRegistration", back_populates="webinar", cascade="all, delete-orphan")


class WebinarRegistration(Base):
    __tablename__ = "webinar_registrations"

    id = Column(Integer, primary_key=True, index=True)
    webinar_id = Column(Integer, ForeignKey("webinars.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)

    webinar = relationship("Webinar", back_populates="registrations")
    user = relationship("User", back_populates="webinar_registrations")


class CooperativeTraining(Base):
    __tablename__ = "cooperative_trainings"

    id = Column(Integer, primary_key=True, index=True)
    cooperative_id = Column(Integer, ForeignKey("cooperatives.id"), nullable=False)
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String, nullable=False)
    description = Column(String, nullable=True)
    session_date = Column(DateTime, nullable=False)
    capacity = Column(Integer, default=20)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    cooperative = relationship("Cooperative", back_populates="cooperative_trainings")
    organizer = relationship("User", back_populates="cooperative_trainings")
    participants = relationship("TrainingParticipant", back_populates="training", cascade="all, delete-orphan")


class TrainingParticipant(Base):
    __tablename__ = "training_participants"

    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey("cooperative_trainings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

    training = relationship("CooperativeTraining", back_populates="participants")
    user = relationship("User", back_populates="training_participations")


class RecyclingRecord(Base):
    __tablename__ = "recycling_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    material_type = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    outcome = Column(String, nullable=True)
    collection_location = Column(String, nullable=True)
    reuse_plan = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="recycling_records")


class EscrowContract(Base):
    """Contrats Escrow pour transactions blockchain sécurisées"""
    __tablename__ = "escrow_contracts"

    id = Column(Integer, primary_key=True, index=True)
    contract_address = Column(String, unique=True, nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("marketplace_transactions.id"), nullable=True)
    buyer_wallet = Column(String, nullable=False)
    seller_wallet = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="XOF")
    status = Column(String, default="locked", index=True)  # locked, funded, released, refunded
    release_conditions = Column(JSON, nullable=True)
    deployed_at = Column(DateTime, default=datetime.datetime.utcnow)
    released_at = Column(DateTime, nullable=True)
    tx_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class AgriculturalNFT(Base):
    """NFT pour traçabilité et certification agricoles"""
    __tablename__ = "agricultural_nfts"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, nullable=False, index=True)
    contract_address = Column(String, nullable=False)
    owner_wallet = Column(String, nullable=False, index=True)
    trace_id = Column(Integer, ForeignKey("blockchain_traces.id"), nullable=True)
    product_name = Column(String, nullable=False)
    nft_metadata = Column(JSON, nullable=True)  # {"origin": "Mali", "certification": "Organic", ...}
    token_uri = Column(String, nullable=True)
    minted_at = Column(DateTime, default=datetime.datetime.utcnow)
    transferred_at = Column(DateTime, nullable=True)
    tx_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    trace = relationship("BlockchainTrace", back_populates="nfts")
