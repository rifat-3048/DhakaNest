import Link from "next/link";

export default function HeroSection() {
  return (
    <section className="relative overflow-hidden border-b border-slate-200 bg-[#f3f7f5]">
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute right-[8%] top-8 h-40 w-40 border border-emerald-200/70" />
        <div className="absolute right-[3%] top-28 h-40 w-40 border border-emerald-200/50" />
        <div className="absolute bottom-14 left-[4%] h-px w-40 bg-emerald-300/70" />
      </div>

      <div className="relative mx-auto grid max-w-7xl items-center gap-10 px-4 py-12 sm:px-6 sm:py-16 lg:grid-cols-[0.92fr_1.08fr] lg:px-8 lg:py-20">
        <div className="home-reveal max-w-2xl">
          <p className="inline-flex items-center gap-2 text-xs font-bold uppercase text-emerald-800">
            <span className="h-2 w-2 rounded-full bg-emerald-600" aria-hidden="true" />
            Location-aware rental discovery
          </p>
          <h1 className="mt-5 text-4xl font-bold leading-tight text-slate-950 sm:text-5xl lg:text-6xl">
            Find the right home in Dhaka, matched to what matters to you.
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">
            DhakaNest brings location, budget, property needs, important
            destinations, and commute preferences into one thoughtful rental
            search experience.
          </p>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/register"
              className="inline-flex min-h-12 items-center justify-center rounded-lg bg-emerald-700 px-6 text-sm font-semibold text-white transition hover:bg-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2"
            >
              Find Your Home
              <ArrowIcon />
            </Link>
            <Link
              href="/register"
              className="inline-flex min-h-12 items-center justify-center rounded-lg border border-slate-300 bg-white px-6 text-sm font-semibold text-slate-800 transition hover:border-slate-400 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600"
            >
              List a Property
            </Link>
          </div>

          <div className="mt-7 flex items-start gap-3 border-t border-slate-200 pt-5 text-sm leading-6 text-slate-600">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
              <CheckIcon />
            </span>
            <p>
              Listings are designed to pass administrator review, supported by
              an advisory rent-fairness assessment.
            </p>
          </div>
        </div>

        <ProductPreview />
      </div>
    </section>
  );
}

function ProductPreview() {
  return (
    <div className="home-reveal home-reveal-delay relative mx-auto w-full max-w-2xl lg:mx-0">
      <div className="absolute -left-5 top-24 hidden w-40 rounded-lg border border-slate-200 bg-white p-3 shadow-md xl:block">
        <p className="text-[11px] font-semibold uppercase text-slate-500">
          Important destination
        </p>
        <p className="mt-1 text-sm font-bold text-slate-900">
          University of Dhaka
        </p>
        <p className="mt-1 text-xs text-emerald-700">30 min preference</p>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-300 bg-white shadow-xl shadow-slate-900/10">
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-950 px-4 py-3 text-white sm:px-5">
          <div>
            <p className="text-xs font-semibold text-emerald-300">DhakaNest</p>
            <p className="text-sm font-bold">Rental match preview</p>
          </div>
          <span className="rounded-full border border-slate-600 px-3 py-1 text-[11px] font-medium text-slate-300">
            Concept interface
          </span>
        </div>

        <div className="grid gap-0 md:grid-cols-[0.9fr_1.1fr]">
          <div className="border-b border-slate-200 bg-slate-50 p-4 sm:p-5 md:border-b-0 md:border-r">
            <p className="text-xs font-bold uppercase text-slate-500">
              Your preferences
            </p>
            <div className="mt-4">
              <PreviewLabel>Preferred areas</PreviewLabel>
              <div className="mt-2 flex flex-wrap gap-2">
                {['Dhanmondi', 'Uttara', 'Mohammadpur'].map((area) => (
                  <span
                    key={area}
                    className="rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold text-emerald-800"
                  >
                    {area}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <PreviewFact label="Budget" value="BDT 18k-35k" />
              <PreviewFact label="Bedrooms" value="2+ rooms" />
            </div>
            <div className="mt-4 rounded-lg border border-slate-200 bg-white p-3">
              <PreviewLabel>Ranking priorities</PreviewLabel>
              <div className="mt-3 space-y-2">
                <PriorityBar label="Location" width="w-full" />
                <PriorityBar label="Budget" width="w-5/6" />
                <PriorityBar label="Amenities" width="w-3/5" />
              </div>
            </div>
          </div>

          <div className="p-4 sm:p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase text-slate-500">
                  Designed recommendation view
                </p>
                <h2 className="mt-1 text-lg font-bold text-slate-950">
                  Homes aligned to your search
                </h2>
              </div>
              <span className="rounded-full bg-amber-50 px-2.5 py-1 text-[10px] font-bold text-amber-800">
                Preview only
              </span>
            </div>

            <div className="mt-4 space-y-3">
              <PropertyPreview
                title="Apartment profile"
                area="Dhanmondi"
                rent="Within selected budget"
                accent="bg-emerald-700"
              />
              <PropertyPreview
                title="Family home profile"
                area="Uttara"
                rent="Strong location fit"
                accent="bg-sky-700"
              />
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-800">
                <CheckIcon /> Administrator reviewed
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold text-slate-700">
                <ChartIcon /> Rent assessment
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PropertyPreview({
  title,
  area,
  rent,
  accent,
}: {
  title: string;
  area: string;
  rent: string;
  accent: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-200 p-3">
      <div className={`h-14 w-16 shrink-0 rounded-md ${accent} p-2`} aria-hidden="true">
        <div className="h-full border border-white/40">
          <div className="mx-auto mt-2 h-2 w-5 bg-white/80" />
          <div className="mx-auto mt-1 h-4 w-3 bg-white/60" />
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-slate-900">{title}</p>
        <p className="mt-0.5 text-xs text-slate-500">{area}</p>
        <p className="mt-1 text-[11px] font-semibold text-emerald-700">{rent}</p>
      </div>
      <span className="text-lg font-bold text-emerald-700" aria-label="Strong match">
        +
      </span>
    </div>
  );
}

function PreviewFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="text-[10px] font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-xs font-bold text-slate-900">{value}</p>
    </div>
  );
}

function PreviewLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] font-semibold uppercase text-slate-500">{children}</p>;
}

function PriorityBar({ label, width }: { label: string; width: string }) {
  return (
    <div className="grid grid-cols-[60px_1fr] items-center gap-2">
      <span className="text-[10px] text-slate-600">{label}</span>
      <span className="h-1.5 overflow-hidden rounded-full bg-slate-100">
        <span className={`block h-full rounded-full bg-emerald-600 ${width}`} />
      </span>
    </div>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 20 20" className="ml-2 h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M4 10h12M11 5l5 5-5 5" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
      <path d="m4 10 4 4 8-8" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M4 16V9m6 7V4m6 12v-5" />
    </svg>
  );
}
