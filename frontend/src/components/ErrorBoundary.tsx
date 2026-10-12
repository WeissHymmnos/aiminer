import React, { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "32px", maxWidth: "800px", margin: "0 auto" }}>
          <div className="card" style={{ height: "auto", border: "1px solid var(--ctp-red)" }}>
            <div className="card-header">
              <h2 style={{ color: "var(--ctp-red)" }}>
                {this.props.fallbackTitle || "Something went wrong in this view"}
              </h2>
            </div>
            <div className="card-body">
              <p className="muted" style={{ margin: 0 }}>
                An unexpected runtime error occurred while rendering this component:
              </p>
              <div className="status-block error" style={{ margin: "8px 0" }}>
                <strong>{this.state.error?.name || "Error"}: </strong>
                <span>{this.state.error?.message || "Unknown error"}</span>
              </div>
              <div className="button-group" style={{ marginTop: "12px" }}>
                <button
                  type="button"
                  className="button"
                  onClick={this.handleReset}
                >
                  Try Again
                </button>
                <button
                  type="button"
                  className="button"
                  onClick={() => window.location.reload()}
                >
                  Reload Page
                </button>
                <button
                  type="button"
                  className="button"
                  onClick={() => {
                    window.location.href = "/";
                  }}
                >
                  Return to Alpha Pool
                </button>
              </div>
              {this.state.errorInfo?.componentStack ? (
                <details style={{ marginTop: "16px" }}>
                  <summary className="muted" style={{ cursor: "pointer", fontSize: "0.85rem" }}>
                    View Component Stack
                  </summary>
                  <pre className="code-block" style={{ marginTop: "8px", fontSize: "0.78rem" }}>
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              ) : null}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
