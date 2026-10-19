import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Financial Research AI | Analyst Workspace",
  description: "Session-scoped financial research, comparison, red flags, and reporting workspace.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-slate-950 text-slate-100">{children}</body>
    </html>
  );
}

