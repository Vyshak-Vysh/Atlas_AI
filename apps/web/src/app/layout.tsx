import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { ThemeScript } from "@/components/shell/ThemeScript";
import { ThemeSync } from "@/components/shell/ThemeSync";
import { AuthProvider } from "@/lib/auth-context";
import { QueryProvider } from "@/lib/query-client";
import { ToastProvider } from "@/lib/toast";

import "@/styles/tokens.css";
import "@/styles/components.css";
import "./globals.css";

// tokens.css's --font-family-sans names "Inter" first, but a CSS font-family
// name alone never fetches the font — without this, every browser silently
// fell back to its own default UI font (Segoe UI / San Francisco / Roboto),
// so the app rendered in a different, unintended typeface per platform.
// next/font self-hosts the font at build time (no runtime Google Fonts
// request) and exposes it as a CSS variable that tokens.css reads.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: "AtlasAI",
  description: "Evidence-backed enterprise project intelligence platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
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
