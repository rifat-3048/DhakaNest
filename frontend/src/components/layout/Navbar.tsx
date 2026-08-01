"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const navigation = [
  { label: "How It Works", href: "/#how-it-works" },
  { label: "For Tenants", href: "/#for-tenants" },
  { label: "For Landlords", href: "/#for-landlords" },
  { label: "About", href: "/#about" },
];

export function Navbar() {
  const pathname = usePathname();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [hasScrolled, setHasScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setHasScrolled(window.scrollY > 8);
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  if (
    pathname.startsWith("/tenant") ||
    pathname.startsWith("/landlord") ||
    pathname.startsWith("/admin")
  ) {
    return null;
  }

  return (
    <header
      className={[
        "sticky top-0 z-50 border-b bg-white/95 transition-shadow",
        hasScrolled
          ? "border-slate-200 shadow-sm"
          : "border-slate-100 shadow-none",
      ].join(" ")}
    >
      <nav
        className="mx-auto flex min-h-[72px] max-w-7xl items-center justify-between gap-5 px-4 sm:px-6 lg:px-8"
        aria-label="Public navigation"
      >
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2"
          onClick={() => setIsMenuOpen(false)}
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-700 text-white">
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M4 11.5 12 5l8 6.5" />
              <path d="M6.5 10.5V20h11v-9.5" />
              <path d="M9.5 20v-5h5v5" />
            </svg>
          </span>
          <span className="text-xl font-bold text-slate-950">DhakaNest</span>
        </Link>

        <div className="hidden items-center gap-7 lg:flex">
          {navigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-sm font-medium text-slate-600 transition hover:text-emerald-700 focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
            >
              {item.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-3 lg:flex">
          <Link
            href="/login"
            className="inline-flex min-h-11 items-center rounded-lg px-4 text-sm font-semibold text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
          >
            Login
          </Link>
          <Link
            href="/register"
            className="inline-flex min-h-11 items-center rounded-lg bg-emerald-700 px-5 text-sm font-semibold text-white hover:bg-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2"
          >
            Register
          </Link>
        </div>

        <button
          type="button"
          aria-label={isMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          aria-expanded={isMenuOpen}
          aria-controls="mobile-public-navigation"
          onClick={() => setIsMenuOpen((open) => !open)}
          className="flex h-11 w-11 items-center justify-center rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 lg:hidden"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            {isMenuOpen ? (
              <>
                <path d="m6 6 12 12" />
                <path d="M18 6 6 18" />
              </>
            ) : (
              <>
                <path d="M4 7h16" />
                <path d="M4 12h16" />
                <path d="M4 17h16" />
              </>
            )}
          </svg>
        </button>
      </nav>

      {isMenuOpen && (
        <div
          id="mobile-public-navigation"
          className="border-t border-slate-200 bg-white px-4 py-5 lg:hidden"
        >
          <div className="mx-auto flex max-w-7xl flex-col gap-1">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsMenuOpen(false)}
                className="rounded-lg px-3 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
              >
                {item.label}
              </Link>
            ))}
            <div className="mt-3 grid grid-cols-2 gap-3 border-t border-slate-200 pt-4">
              <Link
                href="/login"
                onClick={() => setIsMenuOpen(false)}
                className="flex min-h-11 items-center justify-center rounded-lg border border-slate-300 text-sm font-semibold text-slate-700"
              >
                Login
              </Link>
              <Link
                href="/register"
                onClick={() => setIsMenuOpen(false)}
                className="flex min-h-11 items-center justify-center rounded-lg bg-emerald-700 text-sm font-semibold text-white"
              >
                Register
              </Link>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
