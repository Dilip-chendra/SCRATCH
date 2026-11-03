"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api";

interface SuppressionEntry {
  id: string;
  type: "DOMAIN" | "EMAIL";
  value: string;
  reason: string | null;
  created_at: string;
}

export default function SuppressionPage() {
  const { activeWorkspace } = useAuth();
  const [entries, setEntries] = useState<SuppressionEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // New entry form state
  const [type, setType] = useState<"DOMAIN" | "EMAIL">("DOMAIN");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");

  const loadEntries = async () => {
    if (!activeWorkspace) return;
    try {
      setIsLoading(true);
      const data = await apiClient<SuppressionEntry[]>("/api/v1/suppression", {
        workspaceId: activeWorkspace.id,
      });
      setEntries(data || []);
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to load suppression list" });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEntries();
  }, [activeWorkspace]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !value.trim()) return;

    try {
      setIsSubmitting(true);
      setStatusMessage(null);
      await apiClient("/api/v1/suppression", {
        method: "POST",
        workspaceId: activeWorkspace.id,
        body: JSON.stringify({
          type,
          value: value.trim(),
          reason: reason.trim() || undefined,
        }),
      });
      setValue("");
      setReason("");
      setStatusMessage({ type: "success", text: "Suppression entry added successfully." });
      await loadEntries();
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to add suppression entry" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!activeWorkspace) return;
    try {
      await apiClient(`/api/v1/suppression/${id}`, {
        method: "DELETE",
        workspaceId: activeWorkspace.id,
      });
      setEntries(entries.filter((e) => e.id !== id));
      setStatusMessage({ type: "success", text: "Suppression entry removed." });
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to delete entry" });
    }
  };

  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Suppression & Exclusion Lists</h1>
        <p className="text-sm text-text-secondary mt-1">
          Prevent outbound lead generation and email outreach to competitor domains, existing clients, and opted-out contacts.
        </p>
      </div>

      {statusMessage && (
        <div
          className={`rounded-lg p-3 text-xs border ${
            statusMessage.type === "success"
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : "bg-red-500/10 text-red-400 border-red-500/20"
          }`}
        >
          {statusMessage.text}
        </div>
      )}

      {/* Add Entry Card */}
      <div className="rounded-xl border border-surface-border bg-surface p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary mb-4">Add Suppression Rule</h2>
        <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as "DOMAIN" | "EMAIL")}
              className="w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white focus:border-accent focus:outline-none"
            >
              <option value="DOMAIN">Company Domain</option>
              <option value="EMAIL">Contact Email</option>
            </select>
          </div>
          <div className="md:col-span-1">
            <label className="block text-xs font-medium text-text-secondary mb-1">
              {type === "DOMAIN" ? "Domain or Website URL *" : "Email Address *"}
            </label>
            <input
              type="text"
              placeholder={type === "DOMAIN" ? "e.g. competitor.com" : "e.g. lead@target.com"}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
              className="w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
            />
          </div>
          <div className="md:col-span-1">
            <label className="block text-xs font-medium text-text-secondary mb-1">Exclusion Reason</label>
            <input
              type="text"
              placeholder="e.g. Competitor, Current Client, Unsubscribed"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
            />
          </div>
          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {isSubmitting ? "Adding..." : "Add to List"}
            </button>
          </div>
        </form>
      </div>

      {/* Suppression Entries Table */}
      <div className="rounded-xl border border-surface-border bg-surface overflow-hidden">
        <div className="p-4 border-b border-surface-border flex justify-between items-center">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
            Enforced Rules ({entries.length})
          </h2>
        </div>

        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-surface-border border-t-accent" />
          </div>
        ) : entries.length === 0 ? (
          <div className="p-12 text-center text-xs text-text-muted">
            No suppression rules active in this workspace.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-border bg-surface-elevated/40 text-text-secondary font-medium">
                <tr>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Value</th>
                  <th className="py-3 px-4">Reason</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-surface-elevated/30 transition-colors">
                    <td className="py-3 px-4">
                      <span
                        className={`rounded px-1.5 py-0.5 text-[10px] font-mono font-semibold ${
                          entry.type === "DOMAIN"
                            ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                            : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                        }`}
                      >
                        {entry.type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-medium text-white">{entry.value}</td>
                    <td className="py-3 px-4 text-text-secondary">{entry.reason || "—"}</td>
                    <td className="py-3 px-4 text-text-muted">
                      {new Date(entry.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="text-text-muted hover:text-red-400 transition-colors"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
