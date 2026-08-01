"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { clearStoredAuth, getAccessToken, getStoredUser } from "@/lib/auth";

export default function TenantShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    const token = getAccessToken();
    const user = getStoredUser();

    if (!token || !user) {
      clearStoredAuth();
      router.replace("/login");
      return;
    }
    if (user.role === "landlord") {
      router.replace("/landlord/dashboard");
      return;
    }
    if (user.role === "admin") {
      router.replace("/admin/dashboard");
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
        <p className="text-sm text-slate-600">Verifying tenant access...</p>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <p className="text-sm font-medium text-emerald-700">DhakaNest</p>
            <p className="text-lg font-bold text-slate-950">Tenant Portal</p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Log out
          </button>
        </div>
      </header>
      {children}
    </div>
  );
}
