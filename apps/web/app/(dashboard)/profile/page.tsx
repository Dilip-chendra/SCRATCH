"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api";

interface BusinessProfile {
  company_name: string;
  website_url: string;
  industry: string;
  products_services: Array<{ name: string; description?: string }>;
  value_propositions: string[];
  target_industries: string[];
  ideal_customer_profiles: Array<{ title: string; criteria?: string }>;
  disqualification_rules: string[];
}

export default function BusinessProfilePage() {
  const { activeWorkspace } = useAuth();
  const [profile, setProfile] = useState<BusinessProfile>({
    company_name: "",
    website_url: "",
    industry: "",
    products_services: [],
    value_propositions: [],
    target_industries: [],
    ideal_customer_profiles: [],
    disqualification_rules: [],
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Inputs for adding items
  const [newValueProp, setNewValueProp] = useState("");
  const [newTargetIndustry, setNewTargetIndustry] = useState("");
  const [newDisqualRule, setNewDisqualRule] = useState("");
  const [newProdName, setNewProdName] = useState("");
  const [newProdDesc, setNewProdDesc] = useState("");

  useEffect(() => {
    async function loadProfile() {
      if (!activeWorkspace) return;
      try {
        setIsLoading(true);
        const data = await apiClient<BusinessProfile>("/api/v1/business-profile", {
          workspaceId: activeWorkspace.id,
        });
        setProfile({
          company_name: data.company_name || activeWorkspace.name,
          website_url: data.website_url || "",
          industry: data.industry || "",
          products_services: data.products_services || [],
          value_propositions: data.value_propositions || [],
          target_industries: data.target_industries || [],
          ideal_customer_profiles: data.ideal_customer_profiles || [],
          disqualification_rules: data.disqualification_rules || [],
        });
      } catch (err: any) {
        setStatusMessage({ type: "error", text: err.message || "Failed to load profile" });
      } finally {
        setIsLoading(false);
      }
    }
    loadProfile();
  }, [activeWorkspace]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) return;
    try {
      setIsSaving(true);
      setStatusMessage(null);
      await apiClient("/api/v1/business-profile", {
        method: "PUT",
        workspaceId: activeWorkspace.id,
        body: JSON.stringify(profile),
      });
      setStatusMessage({ type: "success", text: "Business profile saved successfully." });
    } catch (err: any) {
      setStatusMessage({ type: "error", text: err.message || "Failed to save profile" });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-surface-border border-t-accent" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Business Profile & ICP</h1>
        <p className="text-sm text-text-secondary mt-1">
          Configure your product positioning, value propositions, and disqualification criteria for lead qualification.
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

      <form onSubmit={handleSave} className="space-y-6">
        {/* Basic Details Card */}
        <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">Company Overview</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Company Name *</label>
              <input
                type="text"
                value={profile.company_name}
                onChange={(e) => setProfile({ ...profile, company_name: e.target.value })}
                required
                className="w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Website URL</label>
              <input
                type="text"
                placeholder="https://example.com"
                value={profile.website_url}
                onChange={(e) => setProfile({ ...profile, website_url: e.target.value })}
                className="w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-xs font-medium text-text-secondary mb-1">Primary Industry</label>
              <input
                type="text"
                placeholder="e.g. Enterprise B2B SaaS, DevOps, Cybersecurity"
                value={profile.industry}
                onChange={(e) => setProfile({ ...profile, industry: e.target.value })}
                className="w-full rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
              />
            </div>
          </div>
        </div>

        {/* Value Propositions */}
        <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">Value Propositions</h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. Reduces cloud compute spending by 40% with zero downtime"
              value={newValueProp}
              onChange={(e) => setNewValueProp(e.target.value)}
              className="flex-1 rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
            />
            <button
              type="button"
              onClick={() => {
                if (newValueProp.trim()) {
                  setProfile({
                    ...profile,
                    value_propositions: [...profile.value_propositions, newValueProp.trim()],
                  });
                  setNewValueProp("");
                }
              }}
              className="rounded-lg border border-surface-border bg-surface-elevated px-4 py-2 text-xs font-medium text-accent hover:border-accent"
            >
              Add
            </button>
          </div>
          <div className="space-y-2">
            {profile.value_propositions.map((vp, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-surface-elevated/60 px-3 py-2 text-xs">
                <span className="text-white">{vp}</span>
                <button
                  type="button"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      value_propositions: profile.value_propositions.filter((_, idx) => idx !== i),
                    })
                  }
                  className="text-text-muted hover:text-red-400"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Target Industries */}
        <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">Target Industries</h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. Fintech, Healthcare, Logistics"
              value={newTargetIndustry}
              onChange={(e) => setNewTargetIndustry(e.target.value)}
              className="flex-1 rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
            />
            <button
              type="button"
              onClick={() => {
                if (newTargetIndustry.trim()) {
                  setProfile({
                    ...profile,
                    target_industries: [...profile.target_industries, newTargetIndustry.trim()],
                  });
                  setNewTargetIndustry("");
                }
              }}
              className="rounded-lg border border-surface-border bg-surface-elevated px-4 py-2 text-xs font-medium text-accent hover:border-accent"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {profile.target_industries.map((ind, i) => (
              <span key={i} className="inline-flex items-center gap-1.5 rounded-md border border-surface-border bg-surface-elevated px-2.5 py-1 text-xs text-text-primary">
                {ind}
                <button
                  type="button"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      target_industries: profile.target_industries.filter((_, idx) => idx !== i),
                    })
                  }
                  className="text-text-muted hover:text-red-400"
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Products & Services */}
        <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">Products & Services</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <input
              type="text"
              placeholder="Product Name (e.g. Enterprise Cluster)"
              value={newProdName}
              onChange={(e) => setNewProdName(e.target.value)}
              className="rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
            />
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Description / Tier"
                value={newProdDesc}
                onChange={(e) => setNewProdDesc(e.target.value)}
                className="flex-1 rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
              />
              <button
                type="button"
                onClick={() => {
                  if (newProdName.trim()) {
                    setProfile({
                      ...profile,
                      products_services: [
                        ...profile.products_services,
                        { name: newProdName.trim(), description: newProdDesc.trim() },
                      ],
                    });
                    setNewProdName("");
                    setNewProdDesc("");
                  }
                }}
                className="rounded-lg border border-surface-border bg-surface-elevated px-4 py-2 text-xs font-medium text-accent hover:border-accent"
              >
                Add
              </button>
            </div>
          </div>
          <div className="space-y-2">
            {profile.products_services.map((p, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-surface-elevated/60 px-3 py-2 text-xs">
                <div>
                  <span className="font-semibold text-white">{p.name}</span>
                  {p.description && <span className="ml-2 text-text-secondary">— {p.description}</span>}
                </div>
                <button
                  type="button"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      products_services: profile.products_services.filter((_, idx) => idx !== i),
                    })
                  }
                  className="text-text-muted hover:text-red-400"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Disqualification Rules */}
        <div className="rounded-xl border border-surface-border bg-surface p-6 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">Disqualification Criteria</h2>
          <p className="text-xs text-text-muted">Leads matching these conditions will be excluded from outbound campaigns.</p>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. Under 10 employees, Non-profit, B2C mobile only"
              value={newDisqualRule}
              onChange={(e) => setNewDisqualRule(e.target.value)}
              className="flex-1 rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white placeholder-text-muted focus:border-accent focus:outline-none"
            />
            <button
              type="button"
              onClick={() => {
                if (newDisqualRule.trim()) {
                  setProfile({
                    ...profile,
                    disqualification_rules: [...profile.disqualification_rules, newDisqualRule.trim()],
                  });
                  setNewDisqualRule("");
                }
              }}
              className="rounded-lg border border-surface-border bg-surface-elevated px-4 py-2 text-xs font-medium text-accent hover:border-accent"
            >
              Add
            </button>
          </div>
          <div className="space-y-2">
            {profile.disqualification_rules.map((rule, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-surface-elevated/60 px-3 py-2 text-xs">
                <span className="text-red-300">⚠ {rule}</span>
                <button
                  type="button"
                  onClick={() =>
                    setProfile({
                      ...profile,
                      disqualification_rules: profile.disqualification_rules.filter((_, idx) => idx !== i),
                    })
                  }
                  className="text-text-muted hover:text-red-400"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="rounded-lg bg-accent px-6 py-2.5 text-xs font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save Business Profile"}
          </button>
        </div>
      </form>
    </div>
  );
}
