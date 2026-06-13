import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Top-level error boundary — catches unhandled React render errors
 * and shows a fallback UI with a reload button.
 *
 * PR 5: Wraps the entire app in main.tsx.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary] Caught:', error.message, info.componentStack);
  }

  handleReload = (): void => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p className="error-boundary-detail">
            {this.state.error?.message ?? 'Unknown error'}
          </p>
          <button className="btn btn-start" onClick={this.handleReload}>
            Reload Application
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
