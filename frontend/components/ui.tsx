import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("min-w-0 rounded-[18px] border border-[var(--border)] bg-[var(--card)] shadow-[0_10px_35px_rgba(52,38,31,0.05)]", className)} {...props} />;
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger"; size?: "sm" | "md" }) {
  const variants = {
    primary: "bg-[var(--espresso)] text-[#fffdf8] hover:bg-[#3a2a22]",
    secondary: "border border-[var(--border)] bg-[var(--ivory)] text-[var(--espresso)] hover:bg-[var(--sand)]",
    ghost: "text-[var(--taupe)] hover:bg-[var(--sand)] hover:text-[var(--espresso)]",
    danger: "bg-[var(--danger)] text-[#fffdf8] hover:brightness-95",
  };
  return <button className={cx(
    "inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-xl font-semibold transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#b9855a33] disabled:cursor-not-allowed disabled:opacity-50",
    size === "sm" ? "h-9 px-3 text-sm" : "h-11 px-4 text-sm",
    variants[variant], className,
  )} {...props} />;
}

export function Badge({ children, tone = "neutral", className }: { children: React.ReactNode; tone?: "neutral" | "info" | "warning" | "danger" | "success"; className?: string }) {
  const tones = {
    neutral: "bg-[#eee7dd] text-[#655a52]",
    info: "bg-[#e2eaec] text-[#435c63]",
    warning: "bg-[#f2e1cc] text-[#8b592a]",
    danger: "bg-[#f2dcd7] text-[#8b3e34]",
    success: "bg-[#dee8df] text-[#46604b]",
  };
  return <span className={cx("inline-flex max-w-full items-center whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold leading-4", tones[tone], className)}>{children}</span>;
}

export function Label({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return <label htmlFor={htmlFor} className="mb-2 block text-sm font-semibold text-[var(--espresso)]">{children}</label>;
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cx("h-11 w-full rounded-xl border border-[var(--border)] bg-[var(--ivory)] px-3.5 text-sm text-[var(--espresso)] outline-none transition placeholder:text-[#9b8e83] focus:border-[var(--camel)] focus:ring-4 focus:ring-[#b9855a1a]", className)} {...props} />;
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cx("min-h-28 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--ivory)] px-3.5 py-3 text-sm text-[var(--espresso)] outline-none transition placeholder:text-[#9b8e83] focus:border-[var(--camel)] focus:ring-4 focus:ring-[#b9855a1a]", className)} {...props} />;
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cx("h-11 w-full rounded-xl border border-[var(--border)] bg-[var(--ivory)] px-3.5 text-sm text-[var(--espresso)] outline-none transition focus:border-[var(--camel)] focus:ring-4 focus:ring-[#b9855a1a]", className)} {...props} />;
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-7 flex min-w-0 flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
      <div className="min-w-0">
        {eyebrow ? <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--camel-dark)]">{eyebrow}</p> : null}
        <h1 className="text-balance text-[clamp(1.75rem,2.4vw,2.25rem)] font-semibold leading-tight tracking-[-0.035em] text-[var(--espresso)]">{title}</h1>
        {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--taupe)]">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2 xl:justify-end">{actions}</div> : null}
    </div>
  );
}

export function Spinner() {
  return <span className="inline-block size-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden />;
}
