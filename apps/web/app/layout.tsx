import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import "./globals.css";

export const metadata: Metadata = {
  title: "freakypeeky",
  description: "we see you 👀",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <div className="px-6 pt-4">
          <Link
            href="/"
            className="inline-block transition-all duration-200 hover:scale-110 hover:-rotate-2 active:scale-95 active:rotate-1"
          >
            <Image
              src="/logo.png"
              alt="freakypeeky"
              width={300}
              height={106}
              className="h-24 w-auto drop-shadow-md hover:drop-shadow-xl transition-all duration-200"
              priority
            />
          </Link>
        </div>
        {children}
      </body>
    </html>
  );
}
