"""Custom exceptions for the AutoDS platform."""


class AutoDSError(Exception):
    """Base exception for all AutoDS errors."""
    pass


# =============================================================================
# Data Errors
# =============================================================================

class DataLoadError(AutoDSError):
    """Failed to load data from source."""
    pass


class UnsupportedFormatError(AutoDSError):
    """File format is not supported."""
    pass


class SchemaValidationError(AutoDSError):
    """Prediction data schema doesn't match training data."""
    pass


class DataQualityError(AutoDSError):
    """Data quality issue detected that prevents analysis."""
    pass


class EmptyDataError(AutoDSError):
    """Dataset is empty or has no usable rows after cleaning."""
    pass


class EncodingDetectionError(AutoDSError):
    """Failed to detect file encoding."""
    pass


# =============================================================================
# Domain Errors
# =============================================================================

class DomainDetectionError(AutoDSError):
    """Failed to detect industry domain."""
    pass


class InvalidDomainError(AutoDSError):
    """Specified domain is not supported."""
    pass


# =============================================================================
# Feature Engineering Errors
# =============================================================================

class DataLeakageDetected(AutoDSError):
    """Potential data leakage detected in feature engineering."""
    pass


class InsufficientDataError(AutoDSError):
    """Not enough data for the requested operation."""
    pass


class FeatureCreationError(AutoDSError):
    """Failed to create a feature."""
    pass


# =============================================================================
# Modeling Errors
# =============================================================================

class ModelTrainingError(AutoDSError):
    """Model training failed."""
    pass


class SingleClassError(AutoDSError):
    """Target variable has only one class."""
    pass


class ExtremeImbalanceError(AutoDSError):
    """Target variable is extremely imbalanced (<1% minority class)."""
    pass


class ModelNotFoundError(AutoDSError):
    """Requested model not found in registry or MLflow."""
    pass


class PredictionError(AutoDSError):
    """Failed to generate predictions."""
    pass


# =============================================================================
# Tool Errors
# =============================================================================

class ToolNotFoundError(AutoDSError):
    """Requested tool not found in the tool registry."""
    pass


class ToolExecutionError(AutoDSError):
    """Tool execution failed."""
    pass


# =============================================================================
# Agent Errors
# =============================================================================

class AgentError(AutoDSError):
    """Agent failed during execution."""
    pass


class OrchestratorError(AutoDSError):
    """Orchestrator failed to route or manage workflow."""
    pass


# =============================================================================
# LLM Errors
# =============================================================================

class LLMAPIError(AutoDSError):
    """LLM API call failed."""
    pass


class LLMRateLimitError(LLMAPIError):
    """LLM API rate limit exceeded."""
    pass


class LLMParsingError(AutoDSError):
    """Failed to parse LLM response."""
    pass


# =============================================================================
# Connector Errors
# =============================================================================

class DatabaseConnectionError(AutoDSError):
    """Failed to connect to database."""
    pass


class APIConnectionError(AutoDSError):
    """Failed to connect to external API."""
    pass


class CloudStorageError(AutoDSError):
    """Failed to access cloud storage."""
    pass


# =============================================================================
# Session Errors
# =============================================================================

class SessionNotFoundError(AutoDSError):
    """Requested session not found."""
    pass


class SessionCorruptedError(AutoDSError):
    """Session data is corrupted or incomplete."""
    pass


# =============================================================================
# Report Errors
# =============================================================================

class ReportGenerationError(AutoDSError):
    """Failed to generate report."""
    pass


# =============================================================================
# Validation Errors
# =============================================================================

class EdgeCaseError(AutoDSError):
    """An edge case was detected that needs user attention."""

    def __init__(self, message: str, edge_case_type: str, suggestion: str = ""):
        super().__init__(message)
        self.edge_case_type = edge_case_type
        self.suggestion = suggestion
