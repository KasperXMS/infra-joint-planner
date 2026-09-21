from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Strict immutable base for all cross-component contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)
