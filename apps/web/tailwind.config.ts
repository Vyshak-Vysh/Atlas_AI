import type { Config } from "tailwindcss";

// Wired to the CSS custom properties in src/styles/tokens.css rather than
// duplicating literal hex values here — this file previously had its own
// hardcoded "brand" blue (#1d4ed8/#1e3a8a) that didn't match tokens.css's
// actual brand scale (--color-brand-600: #2879bd) and was never referenced
// by any component, so it silently drifted. Any Tailwind utility class
// built from this config now resolves to the same design tokens the rest
// of the app (components.css, every inline `var(--...)` style) already
// uses, so `bg-brand-600` and `background: var(--color-brand-600)` are
// guaranteed to mean the same color.
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "var(--color-brand-50)",
          100: "var(--color-brand-100)",
          500: "var(--color-brand-500)",
          600: "var(--color-brand-600)",
          700: "var(--color-brand-700)",
          800: "var(--color-brand-800)",
          900: "var(--color-brand-900)",
          950: "var(--color-brand-950)",
          DEFAULT: "var(--color-brand-600)",
        },
        surface: {
          page: "var(--surface-page)",
          card: "var(--surface-card)",
          raised: "var(--surface-raised)",
          subtle: "var(--surface-subtle)",
          muted: "var(--surface-muted)",
        },
        ink: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          tertiary: "var(--text-tertiary)",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
