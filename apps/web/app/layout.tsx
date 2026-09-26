import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import "./globals.css";

export const metadata: Metadata = {
  title: "freakypeeky",
  description: "we see you 👀",
};

function Nav() {
  return (
    <nav className="sticky top-0 z-50 border-b-3 border-freaky-dark bg-bg/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <Link href="/" className="flex items-center gap-2 transition-transform hover:scale-105">
          <Image
            src="/logo.png"
            alt="freakypeeky"
            width={140}
            height={50}
            className="h-10 w-auto"
            priority
          />
        </Link>

        <div className="flex items-center gap-1">
          <NavLink href="/" emoji="🔍">
            Stalk
          </NavLink>
          <NavLink href="/persona" emoji="🎭">
            Persona
          </NavLink>
          <NavLink href="/love-letters" emoji="💌">
            Love Letters
          </NavLink>
        </div>
      </div>
    </nav>
  );
}

function NavLink({
  href,
  emoji,
  children,
}: {
  href: string;
  emoji: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="rounded-full border-2 border-transparent px-4 py-1.5 font-display text-sm font-bold text-freaky-dark transition-all hover:border-freaky-red hover:bg-freaky-red/10 hover:-rotate-1"
    >
      <span className="mr-1">{emoji}</span>
      {children}
    </Link>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <Nav />
        {children}
      </body>
    </html>
  );
}
