"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { clearStoredAuth, getAccessToken, getStoredUser } from "@/lib/auth";

export default function AdminShell({ children }: { children: ReactNode }) {
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

    if (storedUser && storedUser.role !== "admin") {
      router.replace(
        storedUser.role === "landlord"
          ? "/landlord/dashboard"
          : "/tenant/dashboard",
      );
      return;
    }
    setIsAuthorized(true);
  }, [router]);

  function handleLogout() {
    clearStoredAuth();
    router.replace("/login");
  }

  if (!isAuthorized) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-600">Verifying administrator access...</p>
      </main>
    );
  }

  const isQueueActive =
    pathname === "/admin/dashboard" || pathname.startsWith("/admin/listings/");

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-800 bg-slate-950 text-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div>
            <p className="text-sm font-medium text-emerald-400">DhakaNest</p>
            <h1 className="text-xl font-bold">Administrator Portal</h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <nav aria-label="Administrator navigation">
              <Link
                href="/admin/dashboard"
                className={[
                  "rounded-lg px-4 py-2 text-sm font-medium transition",
                  isQueueActive
                    ? "bg-emerald-700 text-white"
                    : "bg-slate-800 text-slate-200 hover:bg-slate-700",
                ].join(" ")}
              >
                Review Queue
              </Link>
            </nav>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
