import type { Metadata } from "next";

import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "TriageIQ · AI Incident Workspace",
  description: "Django-based AI incident triage, review, resolution, and reporting.",
  applicationName: "TriageIQ",
  icons: {
    icon: "/brand/triageiq-icon.svg",
    shortcut: "/brand/triageiq-icon.svg",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><Providers>{children}</Providers></body></html>;
}
