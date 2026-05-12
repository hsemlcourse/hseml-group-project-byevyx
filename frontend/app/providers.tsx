"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { useAppStore } from "@/lib/store";

export const Providers = ({ children }: { children: React.ReactNode }) => {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  const theme = useAppStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("theme-kabu", "theme-washi");
    root.classList.add(theme === "washi" ? "theme-washi" : "theme-kabu");
  }, [theme]);

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
};
