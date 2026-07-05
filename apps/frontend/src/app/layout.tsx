/**
 * Purpose: Root HTML layout wrapper for all Next.js pages.
 * Interactions: Wraps page.tsx output, applies globals.css, and sets site
 * metadata shown in the browser tab.
 */
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Aviation Intelligence Platform",
  description: "Aviation document intelligence and briefing MVP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
