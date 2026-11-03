"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiClient, API_BASE_URL } from "@/lib/api";

interface PreviewData {
  filename: string;
  delimiter: string;
  headers: string[];
  suggested_mappings: Record<string, string>;
  sample_rows: Array<Record<string, string>>;
  total_estimated_rows: number;
}

interface ImportBatchResult {
  batch_id: string;
  filename: string;
  total_rows: number;
  valid_rows: number;
  duplicate_rows: number;
  suppressed_rows: number;
  error_rows: number;
  status: string;
}

interface QuarantinedRow {
  id: string;
  row_number: number;
  status: string;
  raw_data: Record<string, any>;
  error_details: { reason?: string } | null;
}

export default function LeadImportWizard() {
  const { activeWorkspace } = useAuth();

  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});

  const [isImporting, setIsImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportBatchResult | null>(null);
  const [quarantinedRows, setQuarantinedRows] = useState<QuarantinedRow[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const targetFields = [
    { key: "company_name", label: "Company Name", required: false },
    { key: "domain", label: "Domain / Website", required: false },
    { key: "email", label: "Contact Email", required: false },
    { key: "full_name", label: "Full Name", required: false },
    { key: "first_name", label: "First Name", required: false },
    { key: "last_name", label: "Last Name", required: false },
    { key: "title", label: "Job Title", required: false },
    { key: "phone", label: "Phone", required: false },
    { key: "industry", label: "Industry", required: false },
    { key: "city", label: "City", required: false },
    { key: "country", label: "Country", required: false },
  ];

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setErrorMessage(null);
    setImportResult(null);
    setQuarantinedRows([]);

    if (!activeWorkspace) return;

    try {
      setIsUploading(true);
      const formData = new FormData();
      formData.append("file", selectedFile);

      const data = await apiClient<PreviewData>("/api/v1/leads/upload", {
        method: "POST",
        workspaceId: activeWorkspace.id,
        body: formData,
      });

      setPreview(data);
      setColumnMapping(data.suggested_mappings || {});
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to analyze file");
    } finally {
      setIsUploading(false);
    }
  };

  const handleExecuteImport = async () => {
    if (!file || !activeWorkspace) return;

    try {
      setIsImporting(true);
      setErrorMessage(null);

      const formData = new FormData();
      formData.append("file", file);
      formData.append("column_mapping", JSON.stringify(columnMapping));

      const batchData = await apiClient<ImportBatchResult>("/api/v1/leads/import", {
        method: "POST",
        workspaceId: activeWorkspace.id,
        body: formData,
      });

      setImportResult(batchData);

      // Fetch quarantined rows
      if (batchData.suppressed_rows > 0 || batchData.error_rows > 0) {
        const rows = await apiClient<QuarantinedRow[]>(
          `/api/v1/leads/batches/${batchData.batch_id}/rows?limit=100`,
          { workspaceId: activeWorkspace.id }
        );
        setQuarantinedRows(rows.filter((r) => r.status === "SUPPRESSED" || r.status === "ERROR"));
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Import failed");
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Lead Ingestion & Column Mapping</h1>
        <p className="text-sm text-text-secondary mt-1">
          Upload CSV leads with streaming deduplication, canonical domain normalization, and suppression filtering.
        </p>
      </div>

      {errorMessage && (
        <div className="rounded-lg p-3 text-xs bg-red-500/10 text-red-400 border border-red-500/20">
          {errorMessage}
        </div>
      )}

      {/* Step 1: Upload Card */}
      <div className="rounded-xl border border-surface-border bg-surface p-6">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary mb-3">
          1. Select CSV or Tabular File
        </h2>
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <input
            type="file"
            accept=".csv,text/csv,text/plain"
            onChange={handleFileChange}
            className="block w-full text-xs text-text-secondary file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-surface-elevated file:text-accent hover:file:bg-surface-elevated/80 file:cursor-pointer"
          />
          {isUploading && (
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-surface-border border-t-accent" />
              <span>Analyzing file schema...</span>
            </div>
          )}
        </div>
        {preview && (
          <p className="text-xs text-text-muted mt-2">
            Loaded <span className="font-mono text-white">{preview.filename}</span> (delimiter:{" "}
            <span className="font-mono text-accent">'{preview.delimiter}'</span>, ~{preview.total_estimated_rows} rows).
          </p>
        )}
      </div>

      {/* Step 2: Column Mapping & Sample Preview */}
      {preview && !importResult && (
        <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-6">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
              2. Confirm Column Mapping
            </h2>
            <p className="text-xs text-text-muted mt-1">
              Verify how incoming CSV headers map to internal canonical fields.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {targetFields.map((field) => (
              <div key={field.key} className="rounded-lg border border-surface-border bg-surface-elevated p-3">
                <label className="block text-xs font-semibold text-text-secondary mb-1">
                  {field.label} {field.required && <span className="text-red-400">*</span>}
                </label>
                <select
                  value={columnMapping[field.key] || ""}
                  onChange={(e) =>
                    setColumnMapping({
                      ...columnMapping,
                      [field.key]: e.target.value,
                    })
                  }
                  className="w-full rounded border border-surface-border bg-surface px-2.5 py-1.5 text-xs text-white focus:border-accent focus:outline-none"
                >
                  <option value="">— Unmapped —</option>
                  {preview.headers.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          {/* Sample Rows Preview */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-2">
              Preview First {preview.sample_rows.length} Rows
            </h3>
            <div className="overflow-x-auto rounded-lg border border-surface-border bg-surface-elevated/40">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-surface-border text-text-secondary">
                  <tr>
                    {preview.headers.map((h) => (
                      <th key={h} className="py-2 px-3 whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {preview.sample_rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-surface-elevated/20">
                      {preview.headers.map((h) => (
                        <td key={h} className="py-2 px-3 text-white truncate max-w-xs">
                          {row[h] || "—"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={handleExecuteImport}
              disabled={isImporting}
              className="rounded-lg bg-accent px-6 py-2.5 text-xs font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {isImporting ? "Processing Stream..." : "Run Lead Ingestion"}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Import Results Report */}
      {importResult && (
        <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
                3. Import Completed
              </h2>
              <p className="text-xs text-text-muted mt-1 font-mono">
                Batch ID: {importResult.batch_id}
              </p>
            </div>
            <Link
              href="/leads"
              className="rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-black hover:opacity-90 transition-opacity text-center"
            >
              View Leads Directory →
            </Link>
          </div>

          {/* Metric Badges */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div className="rounded-lg border border-surface-border bg-surface-elevated p-3 text-center">
              <div className="text-xl font-bold text-white">{importResult.total_rows}</div>
              <div className="text-[11px] text-text-secondary uppercase mt-0.5">Total Processed</div>
            </div>
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-center">
              <div className="text-xl font-bold text-emerald-400">{importResult.valid_rows}</div>
              <div className="text-[11px] text-emerald-400 uppercase mt-0.5">Valid Ingested</div>
            </div>
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-3 text-center">
              <div className="text-xl font-bold text-blue-400">{importResult.duplicate_rows}</div>
              <div className="text-[11px] text-blue-400 uppercase mt-0.5">Duplicates Skipped</div>
            </div>
            <div className="rounded-lg border border-purple-500/20 bg-purple-500/10 p-3 text-center">
              <div className="text-xl font-bold text-purple-400">{importResult.suppressed_rows}</div>
              <div className="text-[11px] text-purple-400 uppercase mt-0.5">Suppressed</div>
            </div>
            <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-center">
              <div className="text-xl font-bold text-red-400">{importResult.error_rows}</div>
              <div className="text-[11px] text-red-400 uppercase mt-0.5">Errors Quarantined</div>
            </div>
          </div>

          {/* Quarantined Rows Table */}
          {quarantinedRows.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-2">
                Quarantined & Excluded Rows ({quarantinedRows.length})
              </h3>
              <div className="overflow-x-auto rounded-lg border border-surface-border bg-surface-elevated/40">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-surface-border text-text-secondary">
                    <tr>
                      <th className="py-2.5 px-3">Row #</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Reason / Details</th>
                      <th className="py-2.5 px-3">Raw Data Snapshot</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {quarantinedRows.map((r) => (
                      <tr key={r.id} className="hover:bg-surface-elevated/20">
                        <td className="py-2 px-3 font-mono text-white">{r.row_number}</td>
                        <td className="py-2 px-3">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-mono font-semibold ${
                              r.status === "SUPPRESSED"
                                ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                                : "bg-red-500/10 text-red-400 border border-red-500/20"
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-text-secondary">
                          {r.error_details?.reason || JSON.stringify(r.error_details) || "Validation Error"}
                        </td>
                        <td className="py-2 px-3 font-mono text-[11px] text-text-muted truncate max-w-sm">
                          {JSON.stringify(r.raw_data)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="pt-2">
            <button
              type="button"
              onClick={() => {
                setFile(null);
                setPreview(null);
                setImportResult(null);
                setQuarantinedRows([]);
              }}
              className="text-xs text-text-secondary hover:text-white underline underline-offset-4"
            >
              Upload Another File
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
