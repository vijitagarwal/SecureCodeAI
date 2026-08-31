import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureCode AI",
  description: "Local security analysis workspace",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
