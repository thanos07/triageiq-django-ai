"use client";

import { ArrowRight, Bot, FileCheck2, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { Button, Input, Label, Spinner } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { user, loading, login } = useAuth();
  const [email, setEmail] = useState("demo@triageiq.dev");
  const [password, setPassword] = useState("DemoPass123!");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { if (!loading && user) router.replace("/dashboard"); }, [loading, user, router]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true); setError("");
    try { await login(email, password); router.replace("/dashboard"); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to sign in."); }
    finally { setSubmitting(false); }
  }

  return (
    <main className="grid min-h-screen bg-[var(--cream)] lg:grid-cols-[1.08fr_0.92fr]">
      <section className="soft-grid relative hidden overflow-hidden border-r border-[var(--border)] p-12 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -left-24 top-36 size-80 rounded-full bg-[var(--camel-soft)] blur-3xl" />
        <div className="relative">
          <img
            src="/brand/triageiq-logo.svg"
            alt="TriageIQ Incident Workspace"
            className="h-auto w-[270px] max-w-full"
          />
        </div>
        <div className="relative max-w-2xl">
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.2em] text-[var(--camel-dark)]">Calm operations, accountable AI</p>
          <h1 className="text-5xl font-semibold leading-[1.06] tracking-[-0.055em] text-[var(--espresso)]">Move from incident signal to verified resolution.</h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-[var(--taupe)]">A modern Django and AI-agent workflow for severity classification, probable root cause, safe runbooks, human review, remediation, and downloadable resolution reports.</p>
          <div className="mt-10 grid max-w-xl gap-3 sm:grid-cols-3">
            {[{icon:Bot,label:"Four agents"},{icon:FileCheck2,label:"Human review"},{icon:Sparkles,label:"PDF evidence"}].map(({icon:Icon,label}) => <div key={label} className="rounded-2xl border border-[var(--border)] bg-[color:rgba(255,253,248,0.74)] p-4 backdrop-blur"><Icon className="mb-3 size-5 text-[var(--camel-dark)]" /><p className="text-sm font-semibold">{label}</p></div>)}
          </div>
        </div>
        <p className="relative text-xs text-[var(--taupe)]">Built with Django REST Framework, Next.js, PostgreSQL, and GPT-OSS.</p>
      </section>

      <section className="flex items-center justify-center p-5 md:p-10">
        <div className="w-full max-w-md rounded-[24px] border border-[var(--border)] bg-[var(--ivory)] p-7 shadow-[0_28px_80px_rgba(66,49,38,0.10)] md:p-9">
          <div className="mb-8 lg:hidden">
            <img
              src="/brand/triageiq-logo.svg"
              alt="TriageIQ Incident Workspace"
              className="h-auto w-[220px] max-w-full"
            />
          </div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--camel-dark)]">Welcome back</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">Open your incident workspace</h2>
          <p className="mt-3 text-sm leading-6 text-[var(--taupe)]">The seeded demo account is filled in for a fast interviewer walkthrough.</p>
          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></div>
            <div><Label htmlFor="password">Password</Label><Input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></div>
            {error ? <div className="rounded-xl bg-[#f2dcd7] px-4 py-3 text-sm text-[#8b3e34]">{error}</div> : null}
            <Button className="w-full" disabled={submitting}>{submitting ? <><Spinner /> Signing in…</> : <>Sign in <ArrowRight className="size-4" /></>}</Button>
          </form>
          <div className="mt-6 rounded-2xl bg-[#f8f1e7] p-4 text-xs leading-5 text-[var(--taupe)]"><strong className="text-[var(--espresso)]">Demo mode:</strong> No AI key is required. Add a Groq key and set <code>AI_MODE=live</code> to use GPT-OSS.</div>
        </div>
      </section>
    </main>
  );
}
