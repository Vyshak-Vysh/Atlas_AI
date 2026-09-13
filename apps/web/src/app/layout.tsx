import type { Metadata } from "next";

import { ThemeScript } from "@/components/shell/ThemeScript";
import { ThemeSync } from "@/components/shell/ThemeSync";
import { AuthProvider } from "@/lib/auth-context";
import { QueryProvider } from "@/lib/query-client";
import { ToastProvider } from "@/lib/toast";

import "@/styles/tokens.css";
import "@/styles/components.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "AtlasAI",
  description: "Evidence-backed enterprise project intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <ThemeScript />
      </head>
      <body>
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <QueryProvider>
          <AuthProvider>
            <ToastProvider>
              <ThemeSync />
              {children}
            </ToastProvider>
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
