"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Navbar() {
  const pathname = usePathname();

  if (pathname.startsWith("/landlord") || pathname.startsWith("/admin")) {
    return null;
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <Link href="/" className="text-lg font-bold text-slate-950">
          DhakaNest
        </Link>
        <div className="flex items-center gap-3 text-sm font-medium">
          <Link href="/login" className="text-slate-700 hover:text-slate-950">
            Login
          </Link>
          <Link
            href="/register"
            className="rounded-md bg-emerald-700 px-4 py-2 text-white hover:bg-emerald-800"
          >
            Register
          </Link>
        </div>
      </nav>
    </header>
  );
}
