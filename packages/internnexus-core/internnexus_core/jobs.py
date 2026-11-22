"""Shared job domain enums — single source of truth."""

from __future__ import annotations

import enum


class JobSource(enum.Enum):
    greenhouse = "greenhouse"
    lever = "lever"
    ashby = "ashby"
    manual = "manual"


class JobType(enum.Enum):
    internship = "internship"
    full_time = "full_time"
    part_time = "part_time"


class WorkMode(enum.Enum):
    remote = "remote"
    hybrid = "hybrid"
    on_site = "on_site"
