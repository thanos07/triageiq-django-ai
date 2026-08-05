"use client";

import {
  ArrowRight,
  Bot,
  FileCheck2,
  Sparkles,
} from "lucide-react";
import { useRouter } from "next/navigation";
import {
  FormEvent,
  useEffect,
  useState,
} from "react";

import { useAuth } from "@/components/auth-provider";
import {
  Button,
  Input,
  Label,
  Spinner,
} from "@/components/ui";

const DEMO_EMAIL = "demo@triageiq.dev";
const DEMO_PASSWORD = "DemoPass123!";

export default function LoginPage() {
  const router = useRouter();
  const { user, loading, login } = useAuth();

  const [email, setEmail] = useState(
    DEMO_EMAIL,
  );
  const [password, setPassword] = useState(
    DEMO_PASSWORD,
  );
  const [submitting, setSubmitting] =
    useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  async function performLogin(
    loginEmail: string,
    loginPassword: string,
  ) {
    setSubmitting(true);
    setError("");

    try {
      await login(
        loginEmail,
        loginPassword,
      );

      router.replace("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to sign in.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSubmit(
    event: FormEvent,
  ) {
    event.preventDefault();

    await performLogin(
      email,
      password,
    );
  }

  async function handleDemoLogin() {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);

    await performLogin(
      DEMO_EMAIL,
      DEMO_PASSWORD,
    );
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
          <p className="mb-5 text-xs font-bold uppercase tracking-[0.2em] text-[var(--camel-dark)]">
            Calm operations, accountable AI
          </p>

          <h1 className="text-5xl font-semibold leading-[1.06] tracking-[-0.055em] text-[var(--espresso)]">
            Move from incident signal to
            verified resolution.
          </h1>

          <p className="mt-6 max-w-xl text-base leading-8 text-[var(--taupe)]">
            A modern Django and AI-agent
            workflow for severity
            classification, probable root
            cause, safe runbooks, human
            review, remediation, and
            downloadable resolution reports.
          </p>

          <div className="mt-10 grid max-w-xl gap-3 sm:grid-cols-3">
            {[
              {
                icon: Bot,
                label: "Four agents",
              },
              {
                icon: FileCheck2,
                label: "Human review",
              },
              {
                icon: Sparkles,
                label: "PDF evidence",
              },
            ].map(
              ({
                icon: Icon,
                label,
              }) => (
                <div
                  key={label}
                  className="rounded-2xl border border-[var(--border)] bg-[color:rgba(255,253,248,0.74)] p-4 backdrop-blur"
                >
                  <Icon className="mb-3 size-5 text-[var(--camel-dark)]" />

                  <p className="text-sm font-semibold">
                    {label}
                  </p>
                </div>
              ),
            )}
          </div>
        </div>

        <p className="relative text-xs text-[var(--taupe)]">
          Built with Django REST Framework,
          Next.js, PostgreSQL, and GPT-OSS.
        </p>
      </section>

      <section className="flex items-center justify-center p-5 md:p-10">
        <div className="w-full max-w-md">
          <div className="rounded-[24px] border border-[var(--border)] bg-[var(--ivory)] p-7 shadow-[0_28px_80px_rgba(66,49,38,0.10)] md:p-9">
            <div className="mb-8 lg:hidden">
              <img
                src="/brand/triageiq-logo.svg"
                alt="TriageIQ Incident Workspace"
                className="h-auto w-[220px] max-w-full"
              />
            </div>

            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[var(--camel-dark)]">
              Welcome back
            </p>

            <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em]">
              Open your incident workspace
            </h2>

            <p className="mt-3 text-sm leading-6 text-[var(--taupe)]">
              Demo credentials are pre-filled
              so you can explore the incident
              workflow immediately.
            </p>

            <form
              onSubmit={handleSubmit}
              className="mt-8 space-y-5"
            >
              <div>
                <Label htmlFor="email">
                  Email
                </Label>

                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) =>
                    setEmail(
                      event.target.value,
                    )
                  }
                  required
                />
              </div>

              <div>
                <Label htmlFor="password">
                  Password
                </Label>

                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(event) =>
                    setPassword(
                      event.target.value,
                    )
                  }
                  required
                />
              </div>

              {error ? (
                <div className="rounded-xl bg-[#f2dcd7] px-4 py-3 text-sm text-[#8b3e34]">
                  {error}
                </div>
              ) : null}

              <Button
                className="w-full"
                disabled={submitting}
              >
                {submitting ? (
                  <>
                    <Spinner />
                    Signing in…
                  </>
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="size-4" />
                  </>
                )}
              </Button>
            </form>

            <button
              type="button"
              onClick={handleDemoLogin}
              disabled={submitting}
              className="mt-6 flex w-full items-center justify-between gap-4 rounded-2xl border border-transparent bg-[#f8f1e7] p-4 text-left transition hover:border-[var(--camel)] hover:bg-[var(--camel-soft)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--camel)] disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span>
                <strong className="block text-sm text-[var(--espresso)]">
                  Open demo workspace
                </strong>

                <span className="mt-1 block text-xs leading-5 text-[var(--taupe)]">
                  Sign in with the pre-filled
                  demo account and explore the
                  triage workflow.
                </span>
              </span>

              <ArrowRight className="size-4 shrink-0 text-[var(--camel-dark)]" />
            </button>
          </div>

          <p className="mt-5 text-center text-xs text-[var(--taupe)]">
            Built by{" "}
            <a
              href="https://portfolio-rosy-psi-74.vercel.app/"
              target="_blank"
              rel="noreferrer"
              className="font-semibold text-[var(--camel-dark)] underline decoration-[var(--camel)] underline-offset-4 transition hover:text-[var(--espresso)]"
            >
              Md Noor
            </a>
          </p>
        </div>
      </section>
    </main>
  );
}