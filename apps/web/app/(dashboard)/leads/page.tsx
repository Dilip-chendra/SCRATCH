"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api";

interface Company {
  id: string;
  name: string;
  domain: string;
  normalized_domain: string;
  industry: string | null;
  employee_count_range: string | null;
  city: string | null;
  state: string | null;
  country: string | null;
  status: string;
  created_at: string;
}

interface Contact {
  id: string;
  company_id: string | null;
  email: string;
  first_name: string | null;
  last_name: string | null;
  title: string | null;
  phone: string | null;
  linkedin_url: string | null;
  status: string;
  created_at: string;
}

export default function LeadsDirectoryPage() {
  const { activeWorkspace } = useAuth();
  const [activeTab, setActiveTab] = useState<"companies" | "contacts">("companies");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  const [companies, setCompanies] = useState<Company[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Debounce search query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 250);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  useEffect(() => {
    async function fetchData() {
      if (!activeWorkspace) return;
      try {
        setIsLoading(true);
        if (activeTab === "companies") {
          const q = debouncedQuery ? `?query=${encodeURIComponent(debouncedQuery)}` : "";
          const data = await apiClient<Company[]>(`/api/v1/leads/companies${q}`, {
            workspaceId: activeWorkspace.id,
          });
          setCompanies(data || []);
        } else {
          const q = debouncedQuery ? `?query=${encodeURIComponent(debouncedQuery)}` : "";
          const data = await apiClient<Contact[]>(`/api/v1/leads/contacts${q}`, {
            workspaceId: activeWorkspace.id,
          });
          setContacts(data || []);
        }
      } catch (err) {
        console.error("Failed to load directory data:", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [activeWorkspace, activeTab, debouncedQuery]);

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header & CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Leads & Accounts Directory</h1>
          <p className="text-sm text-text-secondary mt-1">
            Canonical company accounts and verified contact leads scoped to this workspace.
          </p>
        </div>
        <Link
          href="/leads/import"
          className="rounded-lg bg-accent px-4 py-2 text-xs font-semibold text-black hover:opacity-90 transition-opacity text-center self-start sm:self-auto"
        >
          + Import Leads CSV
        </Link>
      </div>

      {/* Tabs and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab("companies")}
            className={`rounded-lg px-3.5 py-1.5 text-xs font-medium transition-colors ${
              activeTab === "companies"
                ? "bg-surface-elevated text-white border border-surface-border"
                : "text-text-secondary hover:text-white"
            }`}
          >
            Accounts ({companies.length})
          </button>
          <button
            onClick={() => setActiveTab("contacts")}
            className={`rounded-lg px-3.5 py-1.5 text-xs font-medium transition-colors ${
              activeTab === "contacts"
                ? "bg-surface-elevated text-white border border-surface-border"
                : "text-text-secondary hover:text-white"
            }`}
          >
            Contacts ({contacts.length})
          </button>
        </div>

        <div className="w-full sm:w-72">
          <input
            type="text"
            placeholder={activeTab === "companies" ? "Search accounts or domain..." : "Search contacts or email..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-1.5 text-xs text-white placeholder-text-muted focus:border-accent focus:outline-none"
          />
        </div>
      </div>

      {/* Directory Table */}
      <div className="rounded-xl border border-surface-border bg-surface overflow-hidden">
        {isLoading ? (
          <div className="p-12 text-center">
            <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-surface-border border-t-accent" />
          </div>
        ) : activeTab === "companies" ? (
          companies.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <p className="text-xs text-text-muted">No accounts found in this workspace.</p>
              <Link
                href="/leads/import"
                className="inline-block rounded-lg border border-surface-border bg-surface-elevated px-3.5 py-1.5 text-xs text-accent hover:border-accent transition-colors"
              >
                Import your first CSV lead list
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-surface-border bg-surface-elevated/40 text-text-secondary font-medium">
                  <tr>
                    <th className="py-3 px-4">Account Name</th>
                    <th className="py-3 px-4">Canonical Domain</th>
                    <th className="py-3 px-4">Industry</th>
                    <th className="py-3 px-4">Location</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Added</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {companies.map((co) => (
                    <tr key={co.id} className="hover:bg-surface-elevated/30 transition-colors">
                      <td className="py-3 px-4 font-semibold text-white">{co.name}</td>
                      <td className="py-3 px-4 font-mono text-accent">{co.normalized_domain}</td>
                      <td className="py-3 px-4 text-text-secondary">{co.industry || "—"}</td>
                      <td className="py-3 px-4 text-text-muted">
                        {[co.city, co.state, co.country].filter(Boolean).join(", ") || "—"}
                      </td>
                      <td className="py-3 px-4">
                        <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
                          {co.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-text-muted">
                        {new Date(co.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : contacts.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <p className="text-xs text-text-muted">No contacts found in this workspace.</p>
            <Link
              href="/leads/import"
              className="inline-block rounded-lg border border-surface-border bg-surface-elevated px-3.5 py-1.5 text-xs text-accent hover:border-accent transition-colors"
            >
              Import your first CSV lead list
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-border bg-surface-elevated/40 text-text-secondary font-medium">
                <tr>
                  <th className="py-3 px-4">Contact Name</th>
                  <th className="py-3 px-4">Verified Email</th>
                  <th className="py-3 px-4">Job Title</th>
                  <th className="py-3 px-4">Phone</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Added</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {contacts.map((contact) => (
                  <tr key={contact.id} className="hover:bg-surface-elevated/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-white">
                      {[contact.first_name, contact.last_name].filter(Boolean).join(" ") || "—"}
                    </td>
                    <td className="py-3 px-4 font-mono text-accent">{contact.email}</td>
                    <td className="py-3 px-4 text-text-secondary">{contact.title || "—"}</td>
                    <td className="py-3 px-4 text-text-muted">{contact.phone || "—"}</td>
                    <td className="py-3 px-4">
                      <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
                        {contact.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-text-muted">
                      {new Date(contact.created_at).toLocaleDateString()}
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
