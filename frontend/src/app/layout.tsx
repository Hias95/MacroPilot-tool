import type { Metadata } from "next";
// Schriften aus dem npm-Paket "geist" (lokal gebuendelt): kein Download von Google beim Build, also auch kein
// Fehlschlag in GitHub Actions, wenn fonts.googleapis.com nicht erreichbar ist.
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

export const metadata: Metadata = {
  title: "MacroPilot",
  description:
    "Das Marktklima auf einen Blick: Liquidität, Konjunktur, Marktsignale und Struktur als Score, mit Bewertung und Markttechnik als Overlays.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="de"
      className={`dark ${GeistSans.variable} ${GeistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
