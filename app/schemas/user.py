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

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def model_validate(cls, obj, **kwargs) -> "UserResponse":
        """Build a frontend-compatible User from an ORM User model."""
        if hasattr(obj, "full_name"):
            # Compute initials for avatar fallback
            initials = ""
            if obj.full_name:
                parts = obj.full_name.strip().split()
                initials = "".join(p[0].upper() for p in parts[:2])

            dob_str = None
            if getattr(obj, "dob", None):
                try:
                    dob_str = obj.dob.strftime("%Y-%m-%d")
                except Exception:
                    dob_str = str(obj.dob)

            profile = UserProfileSchema(
                name=obj.full_name or "",
                email=obj.email or "",
                phone=obj.phone or "",
                avatar=initials,
                avatarUrl=obj.avatar_url or None,
                dob=dob_str,
                gender=getattr(obj, "gender", None),
                preferences=getattr(obj, "preferences", None),
                address=AddressSchema(
                    street=getattr(obj, "address_street", None) or "",
                    city=getattr(obj, "address_city", None) or "",
                    state=getattr(obj, "address_state", None) or "",
                    zip=getattr(obj, "address_zip", None) or "",
                ),
            )

            return cls(
                id=str(obj.id),
                name=obj.full_name or "",
                email=obj.email or "",
                role=obj.role,
                profile=profile,
                is_email_verified=getattr(obj, "is_email_verified", False),
                is_active=getattr(obj, "is_active", True),
            )

        # Fallback: use default Pydantic logic (for dict input)
        return super().model_validate(obj, **kwargs)


# ==========================================================
# System User Response for /admin/users
# Mirrors frontend SystemUser type (with permissions object)
# ==========================================================

class PermissionsSchema(BaseModel):
    manageInventory: bool = False
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
                manageInventory=is_admin,
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