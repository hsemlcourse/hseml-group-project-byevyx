import type { Config } from "tailwindcss";

/**
 * KABU palette v2 — "Sumi & Sakura".
 *
 * Goal: keep the Japanese trading-console identity (red/gold, kanji) but lift
 * the page out of the pure-black look. Backgrounds are warm aubergine-charcoal,
 * borders are a soft champagne-gold haze (not heavy burgundy), and trading
 * colours are softened from neon (#00FF7F / #FF4500) to modern matcha /
 * terracotta tones that read better at length.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: ["class"],
  theme: {
    extend: {
      colors: {
        // Layered surfaces — each step lifts ~3% in lightness with the same hue.
        ink: {
          DEFAULT: "#16131C", // body canvas
          50: "#1F1B26", // panel surface
          100: "#2A242F", // hover / raised
          200: "#352D3A", // active / selected
        },
        // Brand accents — softened "modern Edo".
        burgundy: {
          DEFAULT: "#8B3A3A",
          400: "#A85252",
          600: "#6B2727",
        },
        carmine: {
          DEFAULT: "#E63950", // primary CTA red
          400: "#FF5468",
          600: "#B82A3E",
        },
        gold: {
          DEFAULT: "#E8C547", // champagne, less neon
          400: "#F0D26E",
          600: "#B89623",
        },
        ivory: "#F2EAD3",
        // Trading semantics — softer than neon for long sessions.
        emerald: "#7DD3A8", // bull (matcha)
        flame: "#F18B7A", // bear (terracotta)
        // Optional accents — used sparingly for highlights and chips.
        sakura: "#F4A6B0",
        matcha: "#B8C97C",
        indigo: "#6B89B8",
        // Light theme tokens.
        washi: {
          paper: "#F5F1E6",
          ink: "#1F1A24",
          border: "#C9A86A",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui"],
        jp: ["var(--font-noto-jp)", "Noto Sans JP", "serif"],
        mono: ["var(--font-plex-mono)", "IBM Plex Mono", "monospace"],
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
      },
      boxShadow: {
        elevation:
          "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 8px 24px -12px rgba(0,0,0,0.55)",
        glow: "0 0 0 1px rgba(232,197,71,0.18), 0 12px 32px -16px rgba(230,57,80,0.4)",
        seal:
          "0 0 0 1px rgba(232,197,71,0.35), 0 6px 18px -8px rgba(230,57,80,0.45)",
      },
      backgroundImage: {
        // Subtle radial accents for the body — warmth without going light.
        canvas:
          "radial-gradient(circle at 12% -10%, rgba(230,57,80,0.10) 0%, transparent 55%), radial-gradient(circle at 92% 0%, rgba(232,197,71,0.08) 0%, transparent 50%)",
        glass:
          "linear-gradient(180deg, rgba(255,255,255,0.025) 0%, rgba(255,255,255,0) 60%)",
        sumi:
          "linear-gradient(180deg, rgba(232,197,71,0.08) 0%, rgba(232,197,71,0) 50%)",
      },
      keyframes: {
        inkWash: {
          "0%": { opacity: "0", transform: "translateY(4px)", filter: "blur(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)", filter: "blur(0)" },
        },
        ripple: {
          "0%": { transform: "scale(1)", opacity: "0.35" },
          "100%": { transform: "scale(1.4)", opacity: "0" },
        },
        sealHalo: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(232,197,71,0.0)" },
          "50%": { boxShadow: "0 0 0 6px rgba(232,197,71,0.10)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "ink-wash": "inkWash 500ms cubic-bezier(.2,.7,.2,1) both",
        ripple: "ripple 1800ms ease-out infinite",
        "seal-halo": "sealHalo 3200ms ease-in-out infinite",
        shimmer: "shimmer 2400ms linear infinite",
      },
    },
  },
  plugins: [],
};

export default config;
