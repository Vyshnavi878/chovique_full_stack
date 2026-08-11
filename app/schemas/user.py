from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ==========================================================
# Profile Update Payload
# ==========================================================

class ProfileUpdatePayload(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    preferences: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None


# ==========================================================
# Nested Address + Profile (mirrors frontend UserProfile type)
# ==========================================================

class AddressSchema(BaseModel):
    street: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""


class UserProfileSchema(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    avatar: str = ""
    avatarUrl: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    preferences: Optional[str] = None
    address: AddressSchema


# ==========================================================
# User Response — nested shape matching frontend User type
# { id, name, email, role, profile: { name, email, phone, avatar,
#   avatarUrl, dob, gender, preferences, address: { street, city, state, zip } } }
# ==========================================================

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    profile: UserProfileSchema

    # Additional status fields (optional usage on frontend)
    is_email_verified: bool = False
    is_active: bool = True
    has_password: bool = True

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_user(cls, user):
        initials = ""
        if user.full_name:
            initials = "".join(p[0].upper() for p in user.full_name.split()[:2])

        return cls(
            id=str(user.id),
            name=user.full_name,
            email=user.email,
            role=user.role,
            profile=UserProfileSchema(
                name=user.full_name,
                email=user.email,
                phone=user.phone or "",
                avatar=initials,
                avatarUrl=user.avatar_url,
                dob=user.dob.strftime("%Y-%m-%d") if user.dob else None,
                gender=user.gender,
                preferences=None,
                address=AddressSchema(),
            ),
            is_email_verified=user.is_email_verified,
            is_active=user.is_active,
            has_password=bool(user.hashed_password),
        )


# ==========================================================
# System User Response for /admin/users
# Mirrors frontend SystemUser type (with permissions object)
# ==========================================================

class PermissionsSchema(BaseModel):
    viewAnalytics: bool = False
    manageUsers: bool = False
    configureThemes: bool = False
    exportData: bool = False


class SystemUserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    permissions: PermissionsSchema

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_user(cls, user) -> "SystemUserResponse":
        role = user.role
        # Derive permissions from role
        is_superadmin = (role == "superadmin")
        is_admin = (role in ("admin", "superadmin"))
        return cls(
            id=str(user.id),
            name=user.full_name or "",
            email=user.email or "",
            role=role,
            permissions=PermissionsSchema(
                viewAnalytics=is_admin,
                manageUsers=is_superadmin,
                configureThemes=is_superadmin,
                exportData=is_admin,
            ),
        )


# ==========================================================
# Avatar Upload Response
# ==========================================================

class AvatarUploadResponse(BaseModel):
    avatar_url: str


# ==========================================================
# Customer Address Schemas
# ==========================================================

class CustomerAddressCreate(BaseModel):
    title: str = "Home"
    name: str
    street: str
    city: str
    state: str
    zip: str
    phone: str
    isDefault: bool = False


class CustomerAddressResponse(BaseModel):
    id: str
    title: str
    name: str
    street: str
    city: str
    state: str
    zip: str
    phone: str
    isDefault: bool

    model_config = ConfigDict(from_attributes=True)


# ==========================================================
# Notification Response
# ==========================================================

class SupportNotificationResponse(BaseModel):
    id: str
    text: str
    date: str
    read: bool
    type: str = "general"
    referenceId: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)