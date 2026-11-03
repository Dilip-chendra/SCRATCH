"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, activeWorkspace, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-surface-border border-t-accent" />
          <span className="text-xs text-text-secondary font-mono">LOADING WORKSPACE...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const navLinks = [
    { href: "/leads", label: "Directory" },
    { href: "/leads/import", label: "Import Leads" },
    { href: "/profile", label: "Business Profile" },
    { href: "/suppression", label: "Suppression" },
    { href: "/health", label: "System Health" },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background text-text-primary">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-surface-border bg-surface px-6">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <span className="text-base font-bold tracking-tight text-white">SCRATCH</span>
            <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href || (link.href !== "/health" && pathname.startsWith(link.href) && link.href !== "/leads");
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-surface-elevated text-accent border border-accent/20"
                      : "text-text-secondary hover:text-white hover:bg-surface-elevated/50"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Active Workspace Pill */}
          {activeWorkspace && (
            <div className="hidden md:flex items-center gap-2 rounded-md border border-surface-border bg-surface-elevated px-2.5 py-1 text-xs">
              <span className="text-text-secondary">Workspace:</span>
              <span className="font-medium text-text-primary">{activeWorkspace.name}</span>
              {activeWorkspace.role && (
                <span className="rounded bg-accent/10 px-1.5 py-0.5 text-[10px] font-semibold text-accent">
                  {activeWorkspace.role}
                </span>
              )}
            </div>
          )}
        </div>

        {/* User Info & Logout */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:block text-right">
            <div className="text-xs font-medium text-text-primary">{user.full_name}</div>
            <div className="text-[11px] text-text-muted">{user.email}</div>
          </div>

          <button
            onClick={async () => {
              await logout();
              router.push("/login");
            }}
            className="rounded-lg border border-surface-border bg-surface-elevated px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-text-muted hover:text-text-primary"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-8 max-w-7xl w-full mx-auto">{children}</main>
    </div>
  );
}
