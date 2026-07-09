"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getCurrentUser,
  getDashboardPath,
  getStoredToken,
  logoutUser,
} from "@/lib/auth";
import type { User, UserRole } from "@/types/auth";

type DashboardProps = {
  requiredRole: UserRole;
  title: string;
};

export function Dashboard({ requiredRole, title }: DashboardProps) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      const token = getStoredToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const currentUser = await getCurrentUser(token);

        if (currentUser.role !== requiredRole) {
          router.replace(getDashboardPath(currentUser.role));
          return;
        }

        setUser(currentUser);
      } catch {
        logoutUser();
        router.replace("/login");
      } finally {
        setIsLoading(false);
      }
    }

    loadUser();
  }, [requiredRole, router]);

  function handleLogout() {
    logoutUser();
    router.push("/login");
  }

  if (isLoading) {
    return (
      <section className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-slate-600">Loading dashboard...</p>
      </section>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <section className="mx-auto max-w-4xl px-6 py-12">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-slate-950">{title}</h1>
        <div className="mt-6 space-y-2 text-slate-700">
          <p>
            <span className="font-semibold">Name:</span> {user.name}
          </p>
          <p>
            <span className="font-semibold">Email:</span> {user.email}
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="mt-6 rounded-md bg-slate-900 px-4 py-2 font-semibold text-white hover:bg-slate-800"
        >
          Logout
        </button>
      </div>
    </section>
  );
}
