import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { RazorpayStatus } from "@/components/razorpay-status";

export const metadata: Metadata = {
  title: "PayOps AI",
  description: "Payment operations, made clear.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><div className="min-h-screen md:flex"><Sidebar /><main className="min-w-0 flex-1 px-5 py-8 sm:px-8 lg:px-12"><RazorpayStatus />{children}</main></div></body>
    </html>
  );
}
