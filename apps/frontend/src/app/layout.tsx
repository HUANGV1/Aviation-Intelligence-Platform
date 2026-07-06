/**
 * Purpose: Root HTML layout wrapper for all Next.js pages.
 * Interactions: Wraps page.tsx output, applies globals.css, and sets site
 * metadata shown in the browser tab.
 */
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import "./globals.css";

const geistSans = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
});

export const metadata: Metadata = {
  title: "Aviation Intelligence Platform",
  description:
    "Upload aviation PDFs, process documents, and ask cited questions across your document library.",
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#232733",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${geistSans.variable} ${geistMono.variable}`}
    >
      <body className="bg-background font-sans antialiased">{children}</body>
    </html>
  );
}
