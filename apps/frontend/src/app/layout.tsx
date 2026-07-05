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
