from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Any, List, Optional
import re

class CropBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    surface: float = Field(..., ge=0, le=10000)
    planting_date: Optional[datetime] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Le nom ne peut pas être vide')
        return v.strip()

class CropCreate(CropBase):
    pass

class CropResponse(CropBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class CropUpdate(BaseModel):
    name: Optional[str] = None
    surface: Optional[float] = Field(None, ge=0)
    planting_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class BoundaryPoint(BaseModel):
    lat: float
    lon: float

class FieldBase(BaseModel):
    name: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    area_ha: float = Field(0.0, ge=0)
    crop_rotation: Optional[str] = None
    soil_type: Optional[str] = None
    irrigation_system: Optional[str] = None
    satellite_texture: Optional[str] = None
    boundary_points: List[BoundaryPoint] = Field(default_factory=list)
    notes: Optional[str] = None

class FieldCreate(FieldBase):
    pass

class FieldUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    area_ha: Optional[float] = Field(None, ge=0)
    crop_rotation: Optional[str] = None
    soil_type: Optional[str] = None
    irrigation_system: Optional[str] = None
    satellite_texture: Optional[str] = None
    boundary_points: Optional[List[BoundaryPoint]] = None
    notes: Optional[str] = None

class FieldResponse(FieldBase):
    id: int
    owner_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class FinanceRecordBase(BaseModel):
    date: Optional[datetime] = None
    revenue: float = Field(..., ge=0)
    cost: float = Field(..., ge=0)

class FinanceRecordCreate(FinanceRecordBase):
    pass

class FinanceRecordResponse(FinanceRecordBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class LoanBase(BaseModel):
    amount: float = Field(..., gt=0)

class LoanCreate(LoanBase):
    pass

class LoanResponse(LoanBase):
    id: int
    status: str
    requested_date: datetime
    approved_date: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class InsuranceBase(BaseModel):
    type: str
    premium: float = Field(..., ge=0)
    coverage: float = Field(..., gt=0)

class InsuranceCreate(InsuranceBase):
    pass

class InsuranceResponse(InsuranceBase):
    id: int
    status: str
    requested_date: datetime
    approved_date: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class AdminStatsResponse(BaseModel):
    total_users: int
    validated_users: int
    active_users: int
    pending_loans: int
    approved_loans: int
    pending_insurances: int
    approved_insurances: int
    total_revenue: float
    total_cost: float
    total_loan_amount: float = 0.0
    total_insurance_coverage: float = 0.0

class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    village: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    total_surface: float = Field(0.0, ge=0, le=100000)
    is_admin: bool = False
    is_validated: bool = False
    account_type: str = "farmer"
    role: str = "farmer"
    is_active: bool = True

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('L\'email ne peut pas être vide')
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Format d\'email invalide')
        return v.strip().lower()

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r'^[\d\s\+\-\(\)]+$', v):
            raise ValueError('Format de téléphone invalide')
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    village: Optional[str] = None
    region: Optional[str] = None
    total_surface: Optional[float] = Field(None, ge=0)

class UserResponse(UserBase):
    id: int
    crops: List[CropResponse] = []
    finance_records: List[FinanceRecordResponse] = []
    loans: List["LoanResponse"] = []
    insurances: List["InsuranceResponse"] = []
    mfa_enabled: bool = False
    dashboard: Optional[str] = None
    permissions: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class WeatherResponse(BaseModel):
    location: str
    summary: str
    temperature_celsius: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    rainfall: Optional[float] = None
    soil_moisture: Optional[float] = None
    forecast: List[str]
    alert: Optional[str] = None
    source: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class AdvisorResponse(BaseModel):
    recommendation: str
    details: List[str]

class CreditScoreResponse(BaseModel):
    score: int
    rating: str
    details: List[str]

class MarketResponse(BaseModel):
    crop_prices: dict[str, float]
    market_trend: str
    source: str

class SatelliteResponse(BaseModel):
    summary: str
    vegetation_index: Optional[float] = None
    advisor_note: str
    image_url: Optional[str] = None

class DashboardResponse(BaseModel):
    user: UserResponse
    weather: WeatherResponse
    advisor: AdvisorResponse
    total_revenue: float
    total_cost: float
    net_income: float
    credit_score: CreditScoreResponse
    market_info: MarketResponse
    satellite_info: SatelliteResponse
    yield_prediction: Optional[dict[str, Any]] = None
    price_prediction: Optional[dict[str, Any]] = None


class TraceabilityCreate(BaseModel):
    product_id: str
    origin: str
    certification: Optional[str] = None
    product_type: Optional[str] = None
    origin_info: Optional[str] = None
    carbon_score: Optional[float] = None
    durability_label: Optional[str] = None
    qr_code_data: Optional[str] = None
    metadata: Optional[str] = None


class TraceabilityResponse(BaseModel):
    product_id: str
    origin: Optional[str]
    certification: Optional[str]
    product_type: Optional[str]
    origin_info: Optional[str]
    carbon_score: Optional[float]
    durability_label: Optional[str]
    qr_code_data: Optional[str]
    verified: bool
    tx_hash: Optional[str]
    source: str


class BlockchainTraceCreate(BaseModel):
    product_id: Optional[str] = None
    batch_id: Optional[str] = None
    origin: Optional[str] = None
    location: Optional[str] = None
    certification: Optional[str] = None
    origin_certification: Optional[str] = None
    description: Optional[str] = None
    organic: Optional[bool] = False
    bio: Optional[bool] = False
    sustainable: Optional[bool] = False
    durable: Optional[bool] = False
    timestamp: Optional[int] = None


class BlockchainCertificationRequest(BaseModel):
    product_id: str
    certification_type: str


class MintCertificationRequest(BaseModel):
    product_id: str
    certification_type: str


class SustainabilityScoreResponse(BaseModel):
    user_id: int
    sustainability_score: int
    practices_count: int
    co2_reduction_tonnes: float
    biodiversity_score: float
    water_conservation_m3: float
    level: str


class TokenRedemptionRequest(BaseModel):
    user_id: int
    item_type: str
    quantity: int = Field(..., ge=1)


class TokenHistoryEntry(BaseModel):
    id: int
    amount: float
    type: str
    category: Optional[str]
    reason: Optional[str]
    balance_after: Optional[float]
    created_at: datetime
    blockchain_tx: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TokenBalanceResponse(BaseModel):
    user_id: int
    balance: float


class CommunityLeaderboardEntry(BaseModel):
    user_id: int
    full_name: str
    region: Optional[str]
    sustainability_score: int
    level: str
    token_balance: float
    practices_count: int
    co2_reduction: float


class SocialGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    privacy: Optional[str] = "public"


class SocialGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    privacy: str
    creator_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialPostCreate(BaseModel):
    title: str
    content: str
    group_id: Optional[int] = None
    media_url: Optional[str] = None
    experience_share: Optional[bool] = False
    tags: Optional[str] = None


class SocialPostResponse(BaseModel):
    id: int
    author_id: int
    group_id: Optional[int]
    title: str
    content: str
    media_url: Optional[str]
    experience_share: bool
    tags: Optional[str]
    likes: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SocialCommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[int] = None


class SocialCommentResponse(BaseModel):
    id: int
    post_id: int
    author_id: int
    content: str
    parent_comment_id: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningCourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    video_url: Optional[str] = None
    material_url: Optional[str] = None
    level: Optional[str] = "beginner"
    category: Optional[str] = None
    content_type: Optional[str] = "course"
    published: Optional[bool] = True


class LearningCourseResponse(BaseModel):
    id: int
    creator_id: int
    title: str
    description: Optional[str]
    video_url: Optional[str]
    material_url: Optional[str]
    level: str
    category: Optional[str]
    content_type: str
    published: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebinarCreate(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: Optional[int] = 60
    presenter: Optional[str] = None
    video_url: Optional[str] = None
    registration_link: Optional[str] = None
    max_participants: Optional[int] = None


class WebinarResponse(BaseModel):
    id: int
    creator_id: int
    title: str
    description: Optional[str]
    scheduled_at: datetime
    duration_minutes: int
    presenter: Optional[str]
    video_url: Optional[str]
    registration_link: Optional[str]
    max_participants: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebinarRegistrationResponse(BaseModel):
    id: int
    webinar_id: int
    user_id: int
    registered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CooperativeTrainingCreate(BaseModel):
    cooperative_id: int
    topic: str
    description: Optional[str] = None
    session_date: datetime
    capacity: Optional[int] = 20


class CooperativeTrainingResponse(BaseModel):
    id: int
    cooperative_id: int
    organizer_id: int
    topic: str
    description: Optional[str]
    session_date: datetime
    capacity: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingParticipantResponse(BaseModel):
    id: int
    training_id: int
    user_id: int
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningEnrollmentResponse(BaseModel):
    enrollment_id: int
    course_id: int
    course_title: Optional[str] = None
    content_type: Optional[str] = None
    progress_percent: int
    completed: bool
    enrolled_at: datetime
    updated_at: datetime


class CourseProgressUpdate(BaseModel):
    progress_percent: int


class CooperativeCreate(BaseModel):
    name: str
    region: str
    description: Optional[str] = None


class CooperativeResponse(BaseModel):
    id: int
    name: str
    region: Optional[str]
    description: Optional[str]
    founder_id: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CooperativeGroupPurchaseCreate(BaseModel):
    cooperative_id: int
    product_name: str
    quantity_needed: float
    budget_max: float


class CooperativeGroupPurchaseResponse(BaseModel):
    id: int
    cooperative_id: int
    product_name: str
    quantity_needed: float
    quantity_committed: Optional[float] = None
    budget_max: float
    organizer_id: int
    status: str
    created_at: Optional[datetime] = None


class CooperativeContributionCreate(BaseModel):
    cooperative_id: int
    contribution_type: str
    amount: float
    description: Optional[str] = None


class CooperativeJoinPurchase(BaseModel):
    quantity_committed: float


# Security / Admin requests
class MFASetupVerifyRequest(BaseModel):
    totp_code: str


class MFAAuthVerifyRequest(BaseModel):
    username: str
    password: str
    totp_code: str


class MFASetupRequest(BaseModel):
    username: str
    password: str


class MFADisableRequest(BaseModel):
    password: str


class AdminRoleUpdateRequest(BaseModel):
    role: str


class AdminStatusUpdateRequest(BaseModel):
    is_active: bool


class ResourceExchangeCreate(BaseModel):
    resource_type: str
    description: Optional[str] = None
    quantity: float
    unit: str


class ResourceExchangeResponse(ResourceExchangeCreate):
    id: int
    requester_id: int
    status: str
    exchange_partner_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecyclingRecordCreate(BaseModel):
    material_type: str
    quantity: float
    unit: str
    outcome: Optional[str] = None
    collection_location: Optional[str] = None
    reuse_plan: Optional[str] = None


class RecyclingRecordResponse(RecyclingRecordCreate):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# IoT Schemas
class SensorReadingBase(BaseModel):
    sensor_type: str = Field(..., description="Type de capteur (pump_vibration, battery_level, water_flow, soil_moisture)")
    value: float = Field(..., description="Valeur mesurée")
    unit: str = Field(..., description="Unité de mesure (Hz, %, L/min, %)")
    location: Optional[str] = Field(None, description="Localisation GPS ou nom du champ")
    timestamp: Optional[datetime] = Field(None, description="Timestamp de la mesure")

class SensorReadingCreate(SensorReadingBase):
    user_id: int = Field(..., description="ID de l'utilisateur")

class SensorReadingResponse(SensorReadingBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class IoTDashboardResponse(BaseModel):
    user_id: int
    latest_readings: List[SensorReadingResponse]
    predicted_alert: str
    maintenance_due_in_days: Optional[int]
    recommended_action: str
    resource_optimization: dict
    status: str

class IoTAlertResponse(BaseModel):
    alert_type: str
    message: str
    severity: str  # "low", "medium", "high", "critical"
    sensor_id: Optional[str]
    timestamp: datetime
    recommended_action: str


class AlertResponse(BaseModel):
    id: int
    title: str
    message: str
    alert_type: str
    severity: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    user_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SupportMessageResponse(BaseModel):
    id: int
    subject: str
    message: str
    status: Optional[str] = None
    user_id: int
    created_at: datetime
    response: Optional[str] = None
    responded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SupportRespondRequest(BaseModel):
    response: str
