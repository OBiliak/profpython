"""Vehicle record and configuration models of the import/export module."""

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VehicleRecord:
    """One validated vehicle of the catalog."""

    vehicle_id: int
    brand: str
    model: str
    year: int
    price: float
    mileage: int

    def to_dict(self) -> dict[str, object]:
        """Return the record as a dictionary for serialization."""
        return asdict(self)


@dataclass(frozen=True, slots=True)
class InvalidRecord:
    """Input row rejected by validation in tolerant mode."""

    line_number: int
    row: dict[str, object]
    error: str


@dataclass(frozen=True, slots=True)
class InputConfig:
    """Input file settings."""

    path: Path


@dataclass(frozen=True, slots=True)
class OutputConfig:
    """Output files settings."""

    path: Path
    errors_path: Path
    summary_path: Path
    backup: bool


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    """Allowed range of production years."""

    min_year: int
    max_year: int


@dataclass(frozen=True, slots=True)
class FilterConfig:
    """Price range of exported vehicles."""

    min_price: float
    max_price: float


@dataclass(frozen=True, slots=True)
class ProcessingConfig:
    """Processing policy: strict or tolerant mode and progress step."""

    skip_invalid: bool
    progress_every: int


@dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Logging level, log file and rotation settings."""

    level: str
    path: Path
    max_bytes: int
    backup_count: int


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Complete validated application configuration."""

    schema_version: int
    input: InputConfig
    output: OutputConfig
    validation: ValidationConfig
    filter: FilterConfig
    processing: ProcessingConfig
    logging: LoggingConfig
