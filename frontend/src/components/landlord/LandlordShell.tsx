"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import {
  getAccessToken,
  getStoredUser,
  logoutUser,
} from "@/lib/auth";

interface LandlordShellProps {
  children: ReactNode;
}

const navigationItems = [
  { label: "My Listings", href: "/landlord/dashboard" },
  { label: "Add Listing", href: "/landlord/listings/new" },
];

export default function LandlordShell({ children }: LandlordShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    const accessToken = getAccessToken();
    const storedUser = getStoredUser();

    if (!accessToken) {
      router.replace("/login");
      return;
    }

    if (storedUser && storedUser.role !== "landlord") {
      router.replace(
        storedUser.role === "admin" ? "/admin/dashboard" : "/tenant/dashboard",
      );
      return;
    }

    setIsAuthorized(true);
  }, [router]);

  function handleLogout() {
    logoutUser();
    router.push("/login");
  }

  if (!isAuthorized) {
    return (
      <main className="flex min-h-[70vh] items-center justify-center">
        <p className="text-sm text-slate-600">Verifying landlord access...</p>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div>
            <p className="text-sm font-medium text-emerald-700">DhakaNest</p>
            <h1 className="text-xl font-bold text-slate-900">Landlord Portal</h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <nav className="flex flex-wrap gap-2" aria-label="Landlord navigation">
              {navigationItems.map((item) => {
                const isActive =
                  pathname === item.href ||
                  (item.href !== "/landlord/dashboard" &&
                    pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={[
                      "rounded-lg px-4 py-2 text-sm font-medium transition",
                      isActive
                        ? "bg-emerald-700 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200",
                    ].join(" ")}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {children}
    </div>
  );
}
