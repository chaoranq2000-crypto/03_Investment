"""Shared audit result primitives for skill-oriented workflow modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class AuditExitCode(IntEnum):
    """Common exit-code contract used by migrated skill CLIs."""

    PASS = 0
    ERROR = 1
    BLOCKER = 2
    WARNING_ONLY = 3


@dataclass
class ValidationWarning:
    code: str
    message: str
    severity: str = "warning"  # warning | error

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class AuditFinding:
    severity: str
    code: str
    message: str
    path: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
            "detail": self.detail,
        }


@dataclass
class AuditResult:
    name: str
    exit_code: int = int(AuditExitCode.PASS)
    findings: list[AuditFinding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "exit_code": self.exit_code,
            "findings": [finding.to_dict() for finding in self.findings],
            "metadata": self.metadata,
        }
