import type { Metadata } from "next";
import { IBM_Plex_Mono, Inter, Noto_Sans_JP } from "next/font/google";

import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const notoJp = Noto_Sans_JP({
  subsets: ["latin"],
  weight: ["400", "700", "900"],
  variable: "--font-noto-jp",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "KABU 株 — Trading ML",
  description:
    "Японский интерфейс для свинг-трейдинговых ML-прогнозов: свечи, ИИ-сигналы, бэктест.",
  icons: {
    icon: "/favicon.svg",
  },
};

const RootLayout = ({ children }: { children: React.ReactNode }) => (
  <html
    lang="ru"
    className={`${inter.variable} ${notoJp.variable} ${plexMono.variable}`}
  >
    <body className="min-h-screen">
      <Providers>{children}</Providers>
    </body>
  </html>
);

export default RootLayout;
