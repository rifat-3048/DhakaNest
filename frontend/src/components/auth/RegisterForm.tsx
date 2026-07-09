"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { registerUser } from "@/lib/auth";
import type { PublicRegisterRole } from "@/types/auth";

const passwordRules = [
  {
    label: "Minimum 8 characters",
    test: (value: string) => value.length >= 8,
  },
  {
    label: "At least one uppercase letter",
    test: (value: string) => /[A-Z]/.test(value),
  },
  {
    label: "At least one lowercase letter",
    test: (value: string) => /[a-z]/.test(value),
  },
  {
    label: "At least one number",
    test: (value: string) => /[0-9]/.test(value),
  },
  {
    label: "At least one special character",
    test: (value: string) => /[^A-Za-z0-9]/.test(value),
  },
];

const phoneRules = [
  {
    label: "Exactly 11 digits",
    test: (value: string) => value.length === 11,
  },
  {
    label: "Starts with 013, 014, 015, 016, 017, 018, or 019",
    test: (value: string) => /^01[3-9]/.test(value),
  },
  {
    label: "Digits only",
    test: (value: string) => /^\d*$/.test(value),
  },
];

export function RegisterForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<PublicRegisterRole>("tenant");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isPasswordValid = passwordRules.every((rule) => rule.test(password));
  const isPhoneValid = phoneRules.every((rule) => rule.test(phone));

  function handlePhoneChange(value: string) {
    // Keep only digits and cap at 11 local Bangladeshi mobile digits.
    setPhone(value.replace(/\D/g, "").slice(0, 11));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");

    if (!isPasswordValid) {
      setError("Please complete all password requirements before registering.");
      return;
    }
    if (!isPhoneValid) {
      setError("Please enter a valid Bangladeshi mobile number.");
      return;
    }

    setIsSubmitting(true);

    try {
      await registerUser({ name, email, phone, password, role });
      setMessage("Registration successful. Redirecting to login...");
      setTimeout(() => router.push("/login"), 700);
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Registration failed. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="flex min-h-[calc(100vh-65px)] items-center justify-center px-6 py-12">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h1 className="text-2xl font-bold text-slate-950">Create account</h1>
        <p className="mt-2 text-sm text-slate-600">
          Register as a tenant or landlord to start using DhakaNest.
        </p>

        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Name</span>
            <input
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              minLength={2}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-emerald-700"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-emerald-700"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Phone</span>
            <div className="mt-1 flex rounded-md border border-slate-300 bg-white focus-within:border-emerald-700">
              <span className="flex items-center border-r border-slate-300 bg-slate-50 px-3 text-sm font-medium text-slate-700">
                +880
              </span>
              <input
                value={phone}
                onChange={(event) => handlePhoneChange(event.target.value)}
                required
                inputMode="numeric"
                placeholder="01609802468"
                className="w-full rounded-r-md px-3 py-2 outline-none"
              />
            </div>
            <div className="mt-2 rounded-md bg-slate-50 p-3">
              <p className="text-xs font-semibold text-slate-700">
                Phone number must include:
              </p>
              <ul className="mt-2 space-y-1 text-xs">
                {phoneRules.map((rule) => {
                  const passed = rule.test(phone);

                  return (
                    <li
                      key={rule.label}
                      className={
                        passed ? "text-emerald-700" : "text-slate-500"
                      }
                    >
                      {passed ? "Met: " : "Missing: "}
                      {rule.label}
                    </li>
                  );
                })}
              </ul>
            </div>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
              maxLength={72}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-emerald-700"
            />
            <div className="mt-2 rounded-md bg-slate-50 p-3">
              <p className="text-xs font-semibold text-slate-700">
                Password must include:
              </p>
              <ul className="mt-2 space-y-1 text-xs">
                {passwordRules.map((rule) => {
                  const passed = rule.test(password);

                  return (
                    <li
                      key={rule.label}
                      className={
                        passed ? "text-emerald-700" : "text-slate-500"
                      }
                    >
                      {passed ? "Met: " : "Missing: "}
                      {rule.label}
                    </li>
                  );
                })}
              </ul>
            </div>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-slate-700">Role</span>
            <select
              value={role}
              onChange={(event) =>
                setRole(event.target.value as PublicRegisterRole)
              }
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-emerald-700"
            >
              <option value="tenant">Tenant</option>
              <option value="landlord">Landlord</option>
            </select>
          </label>
        </div>

        {message && (
          <p className="mt-4 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            {message}
          </p>
        )}
        {error && (
          <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={isSubmitting || !isPasswordValid || !isPhoneValid}
          className="mt-6 w-full rounded-md bg-emerald-700 px-4 py-2 font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {isSubmitting ? "Creating account..." : "Register"}
        </button>
      </form>
    </section>
  );
}
