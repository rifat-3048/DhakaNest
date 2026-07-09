import Link from "next/link";

export default function HomePage() {
  return (
    <section className="mx-auto flex min-h-[calc(100vh-65px)] w-full max-w-5xl flex-col justify-center px-6 py-16">
      <div className="max-w-2xl">
        <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-emerald-700">
          Dhaka City Rentals
        </p>
        <h1 className="text-4xl font-bold text-slate-950 sm:text-5xl">
          DhakaNest
        </h1>
        <p className="mt-5 text-lg leading-8 text-slate-700">
          A location-aware rental home recommendation system for Dhaka City.
          Start with an account, then future modules will help tenants,
          landlords, and admins manage the rental flow.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/login"
            className="rounded-md bg-emerald-700 px-5 py-3 text-sm font-semibold text-white hover:bg-emerald-800"
          >
            Login
          </Link>
          <Link
            href="/register"
            className="rounded-md border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-900 hover:bg-slate-50"
          >
            Register
          </Link>
        </div>
      </div>
    </section>
  );
}
