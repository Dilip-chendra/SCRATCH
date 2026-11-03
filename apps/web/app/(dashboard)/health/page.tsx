"use client";

import React, { useEffect, useState, useCallback } from "react";
import { API_BASE_URL } from "@/lib/api";

interface ServiceStatus {
  status: "healthy" | "unhealthy" | "degraded";
  latency_ms: number;
  error?: string | null;
}

interface HealthResponse {
  status: "healthy" | "unhealthy" | "degraded";
  environment: string;
  timestamp: string;
  services: {
    database: ServiceStatus;
    redis: ServiceStatus;
    worker: ServiceStatus;
  };
}

export default function HealthPage() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/health`, {
        cache: "no-store",
      });
      const json: HealthResponse = await res.json();
      setData(json);
      setError(null);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to connect to FastAPI backend gateway.");
      }
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-surface-border pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text-primary">
            System Telemetry & Health
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Real-time backend, persistence, and worker connectivity monitoring (Phase 0 Foundation).
          </p>
        </div>

        <button
          onClick={() => {
            setLoading(true);
            fetchHealth();
          }}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg border border-surface-border bg-surface-elevated px-4 py-2 text-xs font-medium text-text-primary transition-colors hover:border-accent hover:text-accent disabled:opacity-50"
        >
          {loading ? (
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-text-muted border-t-accent" />
          ) : (
            <span>↻</span>
          )}
          Refresh Telemetry
        </button>
      </div>

      {/* Global Status Banner */}
      {error ? (
        <div className="rounded-xl border border-status-danger/30 bg-status-danger/10 p-5">
          <div className="flex items-center gap-3">
            <span className="h-3 w-3 rounded-full bg-status-danger animate-pulse" />
            <h3 className="text-sm font-semibold text-status-danger">Backend Unreachable</h3>
          </div>
          <p className="text-xs text-status-danger/90 mt-2 font-mono">{error}</p>
          <p className="text-xs text-text-secondary mt-3">
            Ensure the FastAPI backend is running on <code className="text-accent">{API_BASE_URL}</code>.
          </p>
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Database Card */}
          <div className="rounded-xl border border-surface-border bg-surface p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                PostgreSQL 16 (RLS)
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                  data.services.database.status === "healthy"
                    ? "bg-status-success/10 text-status-success"
                    : "bg-status-danger/10 text-status-danger"
                }`}
              >
                {data.services.database.status}
              </span>
            </div>
            <div className="text-2xl font-mono font-bold text-text-primary">
              {data.services.database.latency_ms > 0
                ? `${data.services.database.latency_ms} ms`
                : "—"}
            </div>
            <p className="text-xs text-text-muted mt-2">
              Connection Pool: <code className="text-text-secondary">asyncpg (scratch_app)</code>
            </p>
            {data.services.database.error && (
              <p className="text-xs text-status-danger mt-2 font-mono">
                {data.services.database.error}
              </p>
            )}
          </div>

          {/* Redis Card */}
          <div className="rounded-xl border border-surface-border bg-surface p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Redis 7 (Broker & Cache)
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                  data.services.redis.status === "healthy"
                    ? "bg-status-success/10 text-status-success"
                    : "bg-status-danger/10 text-status-danger"
                }`}
              >
                {data.services.redis.status}
              </span>
            </div>
            <div className="text-2xl font-mono font-bold text-text-primary">
              {data.services.redis.latency_ms > 0
                ? `${data.services.redis.latency_ms} ms`
                : "—"}
            </div>
            <p className="text-xs text-text-muted mt-2">
              Queue Backend: <code className="text-text-secondary">aioredis (DB 0)</code>
            </p>
            {data.services.redis.error && (
              <p className="text-xs text-status-danger mt-2 font-mono">
                {data.services.redis.error}
              </p>
            )}
          </div>

          {/* Celery Worker Card */}
          <div className="rounded-xl border border-surface-border bg-surface p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Celery Worker Fabric
              </span>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                  data.services.worker.status === "healthy"
                    ? "bg-status-success/10 text-status-success"
                    : "bg-status-warning/10 text-status-warning"
                }`}
              >
                {data.services.worker.status}
              </span>
            </div>
            <div className="text-2xl font-mono font-bold text-text-primary">
              {data.services.worker.status === "healthy" ? "CONNECTED" : "OFFLINE"}
            </div>
            <p className="text-xs text-text-muted mt-2">
              Queue: <code className="text-text-secondary">default (tasks.health_check_ping)</code>
            </p>
          </div>
        </div>
      ) : null}

      {/* Metadata Section */}
      {data && (
        <div className="rounded-xl border border-surface-border bg-surface p-6">
          <h3 className="text-sm font-semibold text-text-primary mb-4">
            Phase 0 Environment Details
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-text-muted block">Environment</span>
              <span className="font-mono text-text-primary font-medium">{data.environment}</span>
            </div>
            <div>
              <span className="text-text-muted block">Backend Gateway</span>
              <span className="font-mono text-accent font-medium">{API_BASE_URL}</span>
            </div>
            <div>
              <span className="text-text-muted block">Server Timestamp</span>
              <span className="font-mono text-text-primary font-medium">
                {new Date(data.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <div>
              <span className="text-text-muted block">Last Client Polled</span>
              <span className="font-mono text-text-primary font-medium">
                {lastChecked ? lastChecked.toLocaleTimeString() : "—"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
