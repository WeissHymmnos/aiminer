from typing import Protocol, Any, Dict, List, Optional, runtime_checkable

@runtime_checkable
class BacktestBackend(Protocol):
    """
    Protocol defining the interface for a backtest evaluator.
    Matches the usage of RiceQuantEval and LocalDataEval (which extends RiceQuantEval).
    Note: Qlib is not abstracted by this protocol.
    """
    ic: float
    rankic: float
    oos_ic: float
    sharpe: float
    max_dd: float
    rre: Optional[float]
    plot_paths: Dict[str, str]
    daily_returns: Dict[str, float]

    def fetch_data(self) -> None:
        """Fetch market data required for backtesting."""
        ...

    def compute_factors(self) -> None:
        """Compute factor values based on expressions."""
        ...

    def run(self) -> None:
        """Execute the backtest and calculate metrics."""
        ...

    def run_robustness_test(self) -> None:
        """Run robustness tests (e.g., noise injection)."""
        ...

    def get_market_regime(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lookback_days: int = 45,
    ) -> str:
        """Get a summary of the market regime for the specified period."""
        ...

    def summary(self) -> None:
        """Print a summary of the backtest results."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """
    Protocol defining the interface for a vector storage collection.
    Matches the usage of chromadb.Collection in RAGModule and LLMWiki.
    """
    def count(self) -> int:
        """Return the number of documents in the collection."""
        ...

    def query(
        self,
        query_texts: List[str],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Query the collection for similar documents."""
        ...

    def add(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str],
        **kwargs: Any
    ) -> None:
        """Add documents to the collection."""
        ...

    def upsert(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        **kwargs: Any
    ) -> None:
        """Update or insert documents in the collection."""
        ...

    def get(
        self,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
        limit: Optional[int] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Get documents from the collection."""
        ...
