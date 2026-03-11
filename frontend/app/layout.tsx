import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "./nav";
import { ThemeProvider } from "./theme-provider";
export const metadata: Metadata = { title: "Nerdy Ad Engine", description: "Autonomous Ad Copy Generation System" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en"><body>
      <ThemeProvider>
        <Nav />
        <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>{children}</main>
      </ThemeProvider>
    </body></html>
  );
}
