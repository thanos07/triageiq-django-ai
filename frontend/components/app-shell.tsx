"use client";

import {
  Activity,
  BookOpen,
  FileText,
  Gauge,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui";

const SIDEBAR_STORAGE_KEY = "triageiq.sidebar.visible";

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/incidents", label: "Incidents", icon: Activity },
  { href: "/runbooks", label: "Runbook library", icon: BookOpen },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarVisible, setSidebarVisible] = useState(true);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    const stored = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
    if (stored !== null) setSidebarVisible(stored === "true");
  }, []);

  function toggleDesktopSidebar() {
    setSidebarVisible((current) => {
      const next = !current;
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      return next;
    });
  }

  if (loading || !user) {
    return <div className="grid min-h-screen place-items-center bg-[var(--cream)] text-sm text-[var(--taupe)]">Opening your workspace…</div>;
  }

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-20 items-center justify-between px-5">
        <Link href="/dashboard" className="flex min-w-0 items-center gap-3" aria-label="TriageIQ dashboard">
          <img
            src="/brand/triageiq-icon.svg"
            alt=""
            aria-hidden="true"
            className="size-12 shrink-0"
          />
          <span className="min-w-0">
            <span className="block truncate text-lg font-bold tracking-[-0.03em] text-[var(--espresso)]">TriageIQ</span>
            <span className="block truncate text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--camel-dark)]">Incident workspace</span>
          </span>
        </Link>
        <button className="grid size-9 shrink-0 place-items-center rounded-lg text-[var(--taupe)] hover:bg-[#e7dac9] md:hidden" onClick={() => setMobileOpen(false)} aria-label="Close navigation">
          <X className="size-5" />
        </button>
      </div>

      <div className="px-4">
        <Link
          href="/incidents/new"
          onClick={() => setMobileOpen(false)}
          className="sidebar-new-incident flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#29231f] px-4 text-sm font-semibold text-[#fffdf8] shadow-sm transition hover:bg-[#3a2a22] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#b9855a33]"
        >
          <Plus className="size-4 shrink-0" aria-hidden />
          <span>New incident</span>
        </Link>
      </div>

      <nav className="mt-7 flex-1 space-y-1 px-3">
        {navigation.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              onClick={() => setMobileOpen(false)}
              className={`flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-semibold transition ${
                active
                  ? "bg-[var(--camel-soft)] text-[var(--espresso)]"
                  : "text-[var(--taupe)] hover:bg-[#eee4d6] hover:text-[var(--espresso)]"
              }`}
            >
              <Icon className="size-[18px] shrink-0" />
              <span>{label}</span>
            </Link>
          );
        })}
        <div className="mt-6 px-3.5 text-[10px] font-bold uppercase tracking-[0.18em] text-[#9b8e83]">Resources</div>
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/docs/`}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-semibold text-[var(--taupe)] transition hover:bg-[#eee4d6] hover:text-[var(--espresso)]"
        >
          <FileText className="size-[18px] shrink-0" />
          <span>API documentation</span>
        </a>
      </nav>

      <div className="border-t border-[var(--border)] p-4">
        <div className="mb-3 rounded-xl bg-[#f7f0e6] p-3">
          <p className="truncate text-sm font-semibold text-[var(--espresso)]">{user.display_name}</p>
          <p className="truncate text-xs capitalize text-[var(--taupe)]">{user.role.replaceAll("_", " ")}</p>
        </div>
        <Button variant="ghost" className="w-full justify-start" onClick={logout}>
          <LogOut className="size-4" /> Sign out
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen overflow-x-hidden bg-[var(--cream)]">
      <aside
        className={`fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-[var(--border)] bg-[var(--sidebar)] transition-transform duration-200 ease-out md:block ${
          sidebarVisible ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-hidden={!sidebarVisible}
      >
        {sidebar}
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 md:hidden">
          <button className="absolute inset-0 bg-black/25" onClick={() => setMobileOpen(false)} aria-label="Close navigation overlay" />
          <aside className="relative h-full w-[min(18rem,86vw)] bg-[var(--sidebar)] shadow-2xl">{sidebar}</aside>
        </div>
      ) : null}

      <main className={`min-h-screen min-w-0 transition-[padding] duration-200 ease-out ${sidebarVisible ? "md:pl-64" : "md:pl-0"}`}>
        <header className="sticky top-0 z-20 flex h-16 min-w-0 items-center gap-3 border-b border-[var(--border)] bg-[color:rgba(246,241,231,0.92)] px-4 backdrop-blur-xl md:px-6 lg:px-8">
          <button
            className="grid size-10 shrink-0 place-items-center rounded-xl border border-[var(--border)] bg-[var(--ivory)] text-[var(--espresso)] shadow-sm transition hover:bg-[var(--sand)] md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
            title="Open navigation"
          >
            <Menu className="size-5" />
          </button>

          <button
            className="hidden size-10 shrink-0 place-items-center rounded-xl border border-[var(--border)] bg-[var(--ivory)] text-[var(--espresso)] shadow-sm transition hover:bg-[var(--sand)] md:grid"
            onClick={toggleDesktopSidebar}
            aria-label={sidebarVisible ? "Hide sidebar" : "Show sidebar"}
            title={sidebarVisible ? "Hide sidebar" : "Show sidebar"}
            aria-pressed={sidebarVisible}
          >
            {sidebarVisible ? <PanelLeftClose className="size-5" /> : <PanelLeftOpen className="size-5" />}
          </button>

          <p className="hidden min-w-0 truncate text-sm text-[var(--taupe)] sm:block">AI-assisted triage with human accountability</p>
          <div className="ml-auto flex shrink-0 items-center gap-2 text-xs font-semibold text-[var(--taupe)]">
            <span className="size-2 rounded-full bg-[var(--success)]" />
            <span className="hidden sm:inline">System ready</span>
          </div>
        </header>

        <div className="mx-auto w-full min-w-0 max-w-[1440px] px-4 py-6 sm:px-5 md:px-6 lg:px-8 lg:py-8">{children}</div>
      </main>
    </div>
  );
}
