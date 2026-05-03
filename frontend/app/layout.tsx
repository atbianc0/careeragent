import type { Metadata } from "next";

import { NavBar } from "@/components/NavBar";

import "./globals.css";

export const metadata: Metadata = {
  title: "CareerAgent",
  description: "Human-in-the-loop job search and application assistant foundation."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <NavBar />
          {children}
        </div>
      </body>
    </html>
  );
}

