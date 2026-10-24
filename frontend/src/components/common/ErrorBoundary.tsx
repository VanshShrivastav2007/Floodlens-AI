import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Terminal } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full min-h-[320px] p-6 flex flex-col items-center justify-center bg-command-950/95 border border-rose-500/40 rounded-xl text-center font-mono z-40 relative">
          <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/40 flex items-center justify-center text-rose-400 mb-4 shadow-glow-alert">
            <AlertTriangle className="w-6 h-6 animate-pulse" />
          </div>

          <h3 className="text-sm uppercase font-bold tracking-wider text-rose-300">
            {this.props.fallbackTitle || 'Component Operational Fault Recovered'}
          </h3>

          <p className="text-xs text-slate-300 mt-2 max-w-md font-sans">
            A non-fatal rendering error occurred. The application remains running and data state has been preserved.
          </p>

          {this.state.error && (
            <div className="mt-3 p-3 bg-command-900 border border-rose-950 rounded-lg max-w-lg w-full text-left overflow-x-auto text-[11px] text-rose-200">
              <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                <Terminal className="w-3 h-3 text-rose-400" />
                <span className="font-semibold text-slate-300">Fault Diagnostic:</span>
              </div>
              <code>{this.state.error.message || String(this.state.error)}</code>
            </div>
          )}

          <div className="mt-5 flex items-center space-x-3">
            <button
              onClick={this.handleReset}
              className="px-4 py-2 rounded bg-gradient-to-r from-rose-600 to-amber-600 hover:from-rose-500 hover:to-amber-500 text-white font-semibold text-xs tracking-wide transition-all shadow-lg flex items-center space-x-2 cursor-pointer"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>RECOVER VIEW</span>
            </button>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded border border-slate-700 bg-command-900 hover:bg-command-800 text-slate-300 text-xs tracking-wide transition-all"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
