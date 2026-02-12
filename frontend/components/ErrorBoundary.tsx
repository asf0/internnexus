"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import Link from "next/link";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors in child components and displays a fallback UI
 * instead of crashing the entire application.
 * 
 * Features:
 * - Graceful error display with user-friendly message
 * - Error details in development mode
 * - Retry functionality
 * - Navigation options
 * - Error logging to console/monitoring
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render shows the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Log to monitoring service in production
    if (process.env.NODE_ENV === "production") {
      // Example: Sentry.captureException(error, { extra: errorInfo });
      this.logError(error, errorInfo);
    }
  }

  private logError(error: Error, errorInfo: ErrorInfo) {
    // Send error to backend logging endpoint
    fetch("/api/log-error", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        error: error.toString(),
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
      }),
    }).catch((err) => {
      // Silent fail - don't crash while logging errors
      console.error("Failed to log error:", err);
    });
  }

  handleRetry = () => {
    // Reset error state and attempt re-render
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-900">
          <div className="mb-6 rounded-full bg-red-100 p-4 dark:bg-red-900">
            <AlertTriangle className="h-12 w-12 text-red-600 dark:text-red-300" />
          </div>

          <h2 className="mb-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
            Something went wrong
          </h2>

          <p className="mb-6 max-w-md text-slate-600 dark:text-slate-400">
            We&apos;re sorry, but something unexpected happened. Our team has been
            notified and we&apos;re working to fix the issue.
          </p>

          <div className="flex gap-4">
            <button
              onClick={this.handleRetry}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </button>

            <Link
              href="/"
              className="flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-6 py-3 font-medium text-slate-700 transition-colors hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
            >
              <Home className="h-4 w-4" />
              Go Home
            </Link>
          </div>

          {/* Show error details in development */}
          {process.env.NODE_ENV === "development" && this.state.error && (
            <div className="mt-8 w-full max-w-2xl rounded-lg border border-red-200 bg-red-50 p-4 text-left dark:border-red-800 dark:bg-red-950">
              <p className="mb-2 font-semibold text-red-800 dark:text-red-200">
                Error Details (Development Only):
              </p>
              <pre className="overflow-x-auto text-sm text-red-700 dark:text-red-300">
                <code>{this.state.error.toString()}</code>
              </pre>
              {this.state.errorInfo && (
                <pre className="mt-4 overflow-x-auto text-sm text-red-600 dark:text-red-400">
                  <code>{this.state.errorInfo.componentStack}</code>
                </pre>
              )}
            </div>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
