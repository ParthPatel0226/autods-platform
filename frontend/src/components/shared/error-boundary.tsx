"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Props {
  children: ReactNode;
  /** Custom fallback element — if provided, replaces the default glass UI */
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

// ─── Component ────────────────────────────────────────────────────────────────

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Surface to console — a real app would send to Sentry etc.
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    if (this.props.fallback) return this.props.fallback;

    return (
      <div className="flex h-full items-center justify-center px-6">
        <div className="flex flex-col items-center gap-6 text-center max-w-md">
          {/* Icon */}
          <div className="rounded-2xl border border-red-500/20 bg-red-500/8 p-5">
            <AlertTriangle
              className="h-10 w-10 text-red-400"
              strokeWidth={1.5}
            />
          </div>

          {/* Heading */}
          <div className="flex flex-col gap-1.5">
            <p className="font-display italic text-xl font-semibold text-foreground">
              Something went wrong
            </p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              An unexpected error occurred. You can try refreshing this section
              or go back to your projects.
            </p>
          </div>

          {/* Dev error detail */}
          {process.env.NODE_ENV === "development" && this.state.error && (
            <pre className="w-full overflow-x-auto rounded-xl border border-white/8 bg-white/4 px-4 py-3 text-left text-[11px] font-mono text-red-400 whitespace-pre-wrap break-words">
              {this.state.error.message}
            </pre>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={this.handleReset}
              className="btn-glow inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Try again
            </button>
            <Link
              href="/projects"
              className="inline-flex items-center justify-center rounded-md border border-white/10 px-4 py-2 text-sm font-medium transition-colors hover:border-white/20 hover:bg-white/5"
            >
              <Home className="mr-2 h-4 w-4" />
              Go to Projects
            </Link>
          </div>
        </div>
      </div>
    );
  }
}
