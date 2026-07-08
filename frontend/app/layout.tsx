import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Model Desk",
  description: "EV-first football match analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body>{children}</body></html>);
}
