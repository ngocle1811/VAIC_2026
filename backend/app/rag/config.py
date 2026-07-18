"""Configuration values for deterministic Phase 1 RAG processing."""

from pydantic import BaseModel, ConfigDict, Field


class ChunkingConfig(BaseModel):
    """Shared chunk sizing configuration measured in Unicode characters."""

    model_config = ConfigDict(frozen=True)

    target_size: int = Field(default=1_200, ge=200)
    max_size: int = Field(default=1_800, ge=300)
    overlap: int = Field(default=150, ge=0)

    def model_post_init(self, __context: object) -> None:
        if self.target_size > self.max_size:
            raise ValueError("target_size must not exceed max_size")
        if self.overlap >= self.target_size:
            raise ValueError("overlap must be smaller than target_size")


DEFAULT_CHUNKING_CONFIG = ChunkingConfig()
