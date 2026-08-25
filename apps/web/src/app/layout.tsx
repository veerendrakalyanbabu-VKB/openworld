import type { Metadata } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { BackendStateProvider } from "@/components/providers/BackendStateProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenWorld — The Trust Layer for the Agentic Internet",
  description: "Human Intent. Machine Execution. Verifiable Results.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <BackendStateProvider>
          <Sidebar />
          <div className="ml-60 min-h-screen flex flex-col">
            <TopBar />
            <main className="flex-1 p-6">{children}</main>
          </div>
          <CommandPalette />
        </BackendStateProvider>
      </body>
    </html>
  );
}
