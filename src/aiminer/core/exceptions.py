"""Structured quant domain and system exceptions for AI Alpha Miner."""

from __future__ import annotations

from typing import Any, Optional


class AIMinerError(Exception):
    """Base exception for all AI Alpha Miner errors."""

    def __init__(self, message: str = "", *args: Any, **kwargs: Any) -> None:
        super().__init__(message, *args)
        self.message = message
        self.extra = kwargs


# --- Quantitative Domain Exceptions ---


class QuantError(AIMinerError):
    """Base exception for quantitative finance domain errors."""


class EvaluationError(QuantError):
    """Raised when factor evaluation or metric computation fails."""


class DataContractError(QuantError, ValueError):
    """Raised when market data violates a required schema or contract."""

    def __init__(
        self, message: str, report: Optional[Any] = None, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(message, *args, **kwargs)
        self.report = report


class MarketDataError(QuantError):
    """Raised when market data fetching, parsing, or alignment fails."""


class PortfolioOptimizationError(QuantError):
    """Raised when portfolio optimization fails to converge or is infeasible."""


class LifecycleError(QuantError):
    """Raised when factor lifecycle state transition or decay tracking fails."""


class FactorSyntaxError(QuantError):
    """Raised when an expression or factor formula contains syntax errors."""


class OrthogonalizationError(QuantError):
    """Raised when matrix inversion or Gram-Schmidt orthogonalization fails."""


# --- LLM Domain Exceptions ---


class LLMError(AIMinerError):
    """Base exception for LLM provider, invocation, or formatting errors."""


class LLMCallError(LLMError):
    """Raised when remote or local LLM inference call fails."""


class LLMParseError(LLMError):
    """Raised when LLM output cannot be parsed into structured format."""


class PromptTemplateError(LLMError):
    """Raised when a prompt template is missing variables or fails to render."""


# --- Workflow & Orchestration Domain Exceptions ---


class WorkflowError(AIMinerError):
    """Base exception for orchestration, task execution, and pipeline flows."""


class AgentExecutionError(WorkflowError):
    """Raised when an individual mining agent encounters an unrecoverable error."""


class TaskStateError(WorkflowError):
    """Raised when a task or run state transition is invalid."""


class ConcurrencyError(WorkflowError):
    """Raised when worker process pools or thread pools fail."""


class ConfigurationError(WorkflowError):
    """Raised when system or run configuration is invalid."""


# --- Storage & Persistence Domain Exceptions ---


class StorageError(AIMinerError):
    """Base exception for database, file storage, and cache failures."""


class DatabaseError(StorageError):
    """Raised when SQLite or persistence operation fails."""


class VectorStoreError(StorageError):
    """Raised when vector database (e.g. Chroma) queries or updates fail."""


class ManifestError(StorageError):
    """Raised when run manifest creation, serialization, or loading fails."""
