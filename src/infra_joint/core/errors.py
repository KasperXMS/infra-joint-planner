from enum import StrEnum

from pydantic import Field

from infra_joint.core.base import ContractModel


class ExecutionErrorCode(StrEnum):
    ARTIFACT_TOO_LARGE = "artifact_too_large"
    CONTEXT_LIMIT_EXCEEDED = "context_limit_exceeded"
    DEPLOYMENT_REQUIRED = "deployment_required"
    MISSING_ARTIFACT = "missing_artifact"
    SURFACE_MISMATCH = "surface_mismatch"
    UNSUPPORTED_MODALITY = "unsupported_modality"
    VALIDATION_FAILED = "validation_failed"


class FailureDetail(ContractModel):
    code: ExecutionErrorCode
    message: str = Field(min_length=1)


class TypedExecutionError(RuntimeError):
    def __init__(self, code: ExecutionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code

    def detail(self) -> FailureDetail:
        return FailureDetail(code=self.code, message=str(self))
