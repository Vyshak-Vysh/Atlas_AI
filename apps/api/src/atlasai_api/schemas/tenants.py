from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, EmailStr


class AddTenantMemberRequest(BaseModel):
    email: EmailStr
    role: str


class TenantMemberResponse(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role: str


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class TenantMemberDetailResponse(BaseModel):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: str
    joined_at: datetime.datetime


class UpdateMemberRoleRequest(BaseModel):
    role: str
