import TenantPreferenceForm from "@/components/tenant/TenantPreferenceForm";

export default function TenantDashboardPage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <p className="text-sm font-semibold text-emerald-700">
            Tenant Dashboard
          </p>
          <h1 className="mt-2 text-3xl font-bold text-slate-950 sm:text-4xl">
            Find a home that fits your needs
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">
            Tell DhakaNest about your housing needs, budget, and the places you
            travel to regularly. Approved homes will be ranked using these
            requirements and your priorities.
          </p>
        </div>
      </section>
      <TenantPreferenceForm />
    </main>
  );
}
