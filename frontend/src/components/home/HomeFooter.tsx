import Link from "next/link";

export default function HomeFooter() {
  return (
    <footer className="border-t border-slate-200 bg-[#f8faf9]">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1fr_auto] lg:px-8">
        <div className="max-w-md">
          <Link href="/" className="text-xl font-bold text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600">
            DhakaNest
          </Link>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            A location-aware rental home recommendation system for Dhaka City,
            connecting preference-led tenant search with reviewed property listings.
          </p>
        </div>
        <nav className="grid grid-cols-2 gap-x-10 gap-y-3 text-sm" aria-label="Footer navigation">
          <Link href="/#for-tenants" className="text-slate-600 hover:text-emerald-700">Tenant</Link>
          <Link href="/#for-landlords" className="text-slate-600 hover:text-emerald-700">Landlord</Link>
          <Link href="/login" className="text-slate-600 hover:text-emerald-700">Login</Link>
          <Link href="/register" className="text-slate-600 hover:text-emerald-700">Register</Link>
        </nav>
      </div>
      <div className="border-t border-slate-200">
        <div className="mx-auto max-w-7xl px-4 py-5 text-xs text-slate-500 sm:px-6 lg:px-8">
          &copy; {new Date().getFullYear()} DhakaNest. University project.
        </div>
      </div>
    </footer>
  );
}
