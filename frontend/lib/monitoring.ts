/**
 * Monitoring and Logging Utilities
 * 
 * Provides centralized error tracking and performance monitoring
 * Can be extended to integrate with services like Sentry, LogRocket, etc.
 */

interface ErrorContext {
  componentStack?: string;
  [key: string]: unknown;
}

interface LogEntry {
  level: "info" | "warn" | "error";
  message: string;
  timestamp: string;
  context?: Record<string, unknown>;
}

/**
 * Logger class for centralized logging
 */
class Logger {
  private logs: LogEntry[] = [];
  private maxLogs = 100;

  /**
   * Log an info message
   */
  info(message: string, context?: Record<string, unknown>): void {
    this.addLog("info", message, context);
  }

  /**
   * Log a warning
   */
  warn(message: string, context?: Record<string, unknown>): void {
    this.addLog("warn", message, context);
  }

  /**
   * Log an error
   */
  error(message: string, error?: Error, context?: Record<string, unknown>): void {
    const errorContext = error
      ? {
          ...context,
          errorMessage: error.message,
          errorStack: error.stack,
        }
      : context;

    this.addLog("error", message, errorContext);

    // Send to monitoring service in production
    if (process.env.NODE_ENV === "production") {
      this.sendToMonitoring(message, error, context);
    }
  }

  /**
   * Get recent logs (for debugging)
   */
  getLogs(): LogEntry[] {
    return [...this.logs];
  }

  /**
   * Clear all logs
   */
  clear(): void {
    this.logs = [];
  }

  private addLog(
    level: LogEntry["level"],
    message: string,
    context?: Record<string, unknown>
  ): void {
    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      context,
    };

    // Add to beginning for reverse chronological order
    this.logs.unshift(entry);

    // Keep only recent logs
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(0, this.maxLogs);
    }

    // Also log to console
    this.consoleLog(entry);
  }

  private consoleLog(entry: LogEntry): void {
    const timestamp = new Date(entry.timestamp).toLocaleTimeString();
    const prefix = `[${timestamp}] ${entry.level.toUpperCase()}:`;

    switch (entry.level) {
      case "info":
        console.log(prefix, entry.message, entry.context || "");
        break;
      case "warn":
        console.warn(prefix, entry.message, entry.context || "");
        break;
      case "error":
        console.error(prefix, entry.message, entry.context || "");
        break;
    }
  }

  private async sendToMonitoring(
    message: string,
    error?: Error,
    context?: Record<string, unknown>
  ): Promise<void> {
    try {
      const payload = {
        message,
        error: error
          ? {
              name: error.name,
              message: error.message,
              stack: error.stack,
            }
          : null,
        context,
        url: typeof window !== "undefined" ? window.location.href : null,
        userAgent: typeof navigator !== "undefined" ? navigator.userAgent : null,
        timestamp: new Date().toISOString(),
      };

      // Send to backend logging endpoint
      // This endpoint should be created in your backend
      await fetch("/api/log-error", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        // Silent fail - don't wait for response
        keepalive: true,
      });
    } catch {
      // Silent fail - don't crash while logging errors
    }
  }
}

// Export singleton instance
export const logger = new Logger();

/**
 * Track performance metrics
 */
export function trackPerformance(metricName: string, value: number): void {
  logger.info(`Performance: ${metricName}`, { value, unit: "ms" });

  // Send to analytics in production
  if (process.env.NODE_ENV === "production" && typeof window !== "undefined") {
    // Example: Send to Google Analytics, Mixpanel, etc.
    // gtag('event', metricName, { value });
  }
}

/**
 * Measure function execution time
 */
export function measurePerformance<T extends (...args: unknown[]) => unknown>(
  fn: T,
  name: string
): T {
  return ((...args: unknown[]) => {
    const start = performance.now();
    const result = fn(...args);

    // Handle both sync and async functions
    if (result instanceof Promise) {
      return result.finally(() => {
        const duration = performance.now() - start;
        trackPerformance(name, duration);
      });
    } else {
      const duration = performance.now() - start;
      trackPerformance(name, duration);
      return result;
    }
  }) as T;
}

/**
 * Web Vitals tracking
 */
export function trackWebVitals(): void {
  if (typeof window === "undefined") return;

  // Largest Contentful Paint
  new PerformanceObserver((list) => {
    const entries = list.getEntries();
    const lastEntry = entries[entries.length - 1];
    trackPerformance("LCP", lastEntry.startTime);
  }).observe({ entryTypes: ["largest-contentful-paint"] });

  // First Input Delay
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      const fidEntry = entry as PerformanceEventTiming;
      const fid = fidEntry.processingStart - fidEntry.startTime;
      trackPerformance("FID", fid);
    }
  }).observe({ entryTypes: ["first-input"] as const });

  // Cumulative Layout Shift
  let clsValue = 0;
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!(entry as { hadRecentInput?: boolean }).hadRecentInput) {
        clsValue += (entry as { value?: number }).value || 0;
      }
    }
    trackPerformance("CLS", clsValue);
  }).observe({ entryTypes: ["layout-shift"] });
}

/**
 * Report error to monitoring
 */
export function reportError(
  error: Error,
  context?: ErrorContext
): void {
  logger.error("Application error", error, context);
}

/**
 * Safe async wrapper that logs errors
 */
export async function safeAsync<T>(
  promise: Promise<T>,
  errorMessage: string
): Promise<T | null> {
  try {
    return await promise;
  } catch (error) {
    logger.error(errorMessage, error instanceof Error ? error : undefined);
    return null;
  }
}
