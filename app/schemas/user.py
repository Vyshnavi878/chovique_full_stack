from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
import re


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

    @field_validator("full_name", "name", mode="before")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            s = str(v).strip()
            if not s:
                raise ValueError("Full Name cannot be empty.")
            if len(s) < 2 or len(s) > 100:
                raise ValueError("Full Name must be between 2 and 100 characters.")
            if not any(c.isalpha() for c in s):
                raise ValueError("Full Name must contain letters.")
            return s
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        if v is not None and str(v).strip():
            s = str(v).strip()
            if not re.match(r"^[6-9]\d{9}$", s):
                raise ValueError("Phone number must be a valid 10-digit Indian number starting with 6, 7, 8, or 9.")
            return s
        return v



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

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v):
        s = str(v or "").strip()
        if not s:
            raise ValueError("Address Label is required.")
        if len(s) < 2 or len(s) > 30:
            raise ValueError("Address Label must be between 2 and 30 characters.")
        if not any(c.isalnum() for c in s):
            raise ValueError("Address Label cannot contain only special characters.")
        return s

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        s = str(v or "").strip()
        if not s:
            raise ValueError("Recipient Full Name is required.")
        if len(s) < 2 or len(s) > 100:
            raise ValueError("Recipient Full Name must be between 2 and 100 characters.")
        if not any(c.isalpha() for c in s):
            raise ValueError("Recipient Full Name must contain valid letters.")
        return s

    @field_validator("street", mode="before")
    @classmethod
    def validate_street(cls, v):
        s = str(v or "").strip()
        if not s:
            raise ValueError("Street Address is required.")
        if len(s) > 250:
            raise ValueError("Street Address cannot exceed 250 characters.")
        return s

    @field_validator("city", mode="before")
    @classmethod
    def validate_city(cls, v):
        s = str(v or "").strip()
        if not s:
            raise ValueError("City is required.")
        if len(s) < 2 or len(s) > 100:
            raise ValueError("City must be between 2 and 100 characters.")
        if s.isdigit():
            raise ValueError("City cannot be numbers-only.")
        return s

    @field_validator("state", mode="before")
    @classmethod
    def validate_state(cls, v):
        s = str(v or "").strip()
        if not s:
            raise ValueError("State is required.")
        return s

    @field_validator("zip", mode="before")
    @classmethod
    def validate_zip(cls, v):
        s = str(v or "").strip()
        if not re.match(r"^\d{6}$", s):
            raise ValueError("PIN/Postal Code must be exactly 6 digits.")
        return s

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        s = str(v or "").strip()
        if not re.match(r"^[6-9]\d{9}$", s):
            raise ValueError("Phone number must be a valid 10-digit Indian number starting with 6, 7, 8, or 9.")
        return s


class CustomerAddressUpdate(BaseModel):
    title: Optional[str] = None
    name: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    isDefault: Optional[bool] = None

    @field_validator("title", mode="before")
    @classmethod
    def validate_title(cls, v):
        if v is not None:
            s = str(v).strip()
            if not s:
                raise ValueError("Address Label cannot be empty.")
            if len(s) < 2 or len(s) > 30:
                raise ValueError("Address Label must be between 2 and 30 characters.")
            if not any(c.isalnum() for c in s):
                raise ValueError("Address Label cannot contain only special characters.")
            return s
        return v

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            s = str(v).strip()
            if not s:
                raise ValueError("Recipient Full Name cannot be empty.")
            if len(s) < 2 or len(s) > 100:
                raise ValueError("Recipient Full Name must be between 2 and 100 characters.")
            if not any(c.isalpha() for c in s):
                raise ValueError("Recipient Full Name must contain valid letters.")
            return s
        return v

    @field_validator("street", mode="before")
    @classmethod
    def validate_street(cls, v):
        if v is not None:
            s = str(v).strip()
            if not s:
                raise ValueError("Street Address cannot be empty.")
            if len(s) > 250:
                raise ValueError("Street Address cannot exceed 250 characters.")
            return s
        return v

    @field_validator("city", mode="before")
    @classmethod
    def validate_city(cls, v):
        if v is not None:
            s = str(v).strip()
            if not s:
                raise ValueError("City cannot be empty.")
            if len(s) < 2 or len(s) > 100:
                raise ValueError("City must be between 2 and 100 characters.")
            if s.isdigit():
                raise ValueError("City cannot be numbers-only.")
            return s
        return v

    @field_validator("zip", mode="before")
    @classmethod
    def validate_zip(cls, v):
        if v is not None and str(v).strip():
            s = str(v).strip()
            if not re.match(r"^\d{6}$", s):
                raise ValueError("PIN/Postal Code must be exactly 6 digits.")
            return s
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def validate_phone(cls, v):
        if v is not None and str(v).strip():
            s = str(v).strip()
            if not re.match(r"^[6-9]\d{9}$", s):
                raise ValueError("Phone number must be a valid 10-digit Indian number starting with 6, 7, 8, or 9.")
            return s
        return v


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