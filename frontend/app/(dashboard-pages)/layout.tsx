import type { Metadata } from "next";
import DashboardNavbar from "@/components/DashboardNavbar";
import DashboardFooter from "@/components/DashboardFooter";

// Note: Fonts and Metadata are typically handled in the root layout, 
// but including them here for completeness if this were a separate entry point.

export const metadata: Metadata = {
  title: "Dashboard | Tool X",
  description: "Manage your intelligent agent deployments.",
};

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
        // The main layout wrapper maintains the dark theme established in the public layout
        <div className="min-h-screen bg-slate-950 text-slate-50 font-sans selection:bg-violet-500/30 flex flex-col">
          <DashboardNavbar />
          {/* Modified: Set max-width to 1640px for a wider dashboard view */}
          <main className="mx-auto px-4 sm:px-6 lg:px-8 py-8 mb-auto w-full max-w-[1640px]">
            {children}
          </main>
          {/* Reusing the existing Footer component */}
          <DashboardFooter /> 
        </div>
  );
}