import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hermes Studio v2",
  description:
    "Local-first autonomous Multi-Agent Game and Software Engineering Workbench.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#141414] text-zinc-100 antialiased selection:bg-zinc-700 selection:text-zinc-100">
        {children}
      </body>
    </html>
  );
}
