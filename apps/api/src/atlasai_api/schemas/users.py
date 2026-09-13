from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    status: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)


class MyTenantMembershipResponse(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    role: str
