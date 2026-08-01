import Link from "next/link";

const benefits = [
  {
    title: "Location-aware matching",
    description: "Broad areas, micro-areas, and important destinations.",
    icon: "pin",
  },
  {
    title: "Budget-conscious",
    description: "Clear rent limits and controlled flexibility.",
    icon: "wallet",
  },
  {
    title: "Reviewed listings",
    description: "Administrator decisions before recommendation eligibility.",
    icon: "shield",
  },
  {
    title: "Rent-fairness insights",
    description: "Advisory model context to support human review.",
    icon: "chart",
  },
] as const;

export default function HomeSections() {
  return (
    <>
      <section className="border-b border-slate-200 bg-white" aria-label="DhakaNest benefits">
        <div className="mx-auto grid max-w-7xl gap-px bg-slate-200 sm:grid-cols-2 lg:grid-cols-4">
          {benefits.map((benefit) => (
            <div key={benefit.title} className="flex gap-3 bg-white px-5 py-6 lg:px-6">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                <BenefitIcon name={benefit.icon} />
              </span>
              <div>
                <h2 className="text-sm font-bold text-slate-950">{benefit.title}</h2>
                <p className="mt-1 text-xs leading-5 text-slate-500">{benefit.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="how-it-works" className="scroll-mt-24 bg-[#f8faf9] py-20 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="How DhakaNest works"
            title="A clearer path from rental needs to trusted choices"
            description="DhakaNest is designed to turn detailed tenant preferences into ranked options from approved, available listings."
          />

          <ol className="mt-12 grid gap-8 lg:grid-cols-3 lg:gap-0">
            <ProcessStep
              number="01"
              title="Tell us what you need"
              description="Choose preferred areas, budget, bedrooms, property requirements, and important destinations."
            />
            <ProcessStep
              number="02"
              title="Receive intelligent recommendations"
              description="The future recommendation engine is designed to rank approved properties against your priorities."
            />
            <ProcessStep
              number="03"
              title="Review trusted listing details"
              description="Once recommendations are generated, compare images, amenities, landlord details, and rent assessments."
            />
          </ol>
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white py-20 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <SectionHeading
            eyebrow="Built for both sides of renting"
            title="One platform for finding and presenting a home"
            description="Focused workflows help tenants express what matters and landlords prepare listings for review."
          />

          <div className="mt-12 grid gap-6 lg:grid-cols-2">
            <RolePanel
              id="for-tenants"
              label="For tenants"
              title="Search with your real priorities"
              description="Build a detailed preference profile before recommendation ranking is connected."
              points={[
                "Choose preferred broad areas and micro-areas",
                "Define budget and property requirements",
                "Prioritize important destinations and commute limits",
                "Prepare for ranked rental options",
              ]}
              action="Start as a Tenant"
              tone="emerald"
            />
            <RolePanel
              id="for-landlords"
              label="For landlords"
              title="Move listings through a clear review process"
              description="Create complete property records and follow their status from draft to decision."
              points={[
                "Create and update property listings",
                "Upload and organize listing images",
                "Submit complete listings for administrator review",
                "Track approval and requested revisions",
              ]}
              action="List Your Property"
              tone="navy"
            />
          </div>
        </div>
      </section>

      <section id="about" className="scroll-mt-24 bg-slate-950 py-20 text-white sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-8 lg:grid-cols-[0.72fr_1.28fr] lg:items-end">
            <div>
              <p className="text-xs font-bold uppercase text-emerald-400">Trust through review</p>
              <h2 className="mt-3 text-3xl font-bold leading-tight sm:text-4xl">
                Technology informs. Administrators decide.
              </h2>
            </div>
            <p className="max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
              The rent-fairness model provides advisory context only. An administrator
              reviews the property information and makes the final decision before a
              listing can become eligible for recommendations.
            </p>
          </div>

          <ol className="mt-12 grid gap-3 md:grid-cols-5">
            {[
              ["01", "Landlord submits", "Property details and images"],
              ["02", "Information checked", "Administrator review"],
              ["03", "Rent assessed", "Advisory model insight"],
              ["04", "Decision recorded", "Human final decision"],
              ["05", "Approved listing", "Eligible for recommendation"],
            ].map(([number, title, description], index) => (
              <li key={number} className="relative border-l border-slate-700 py-2 pl-5 md:border-l-0 md:border-t md:px-3 md:pt-6">
                <span className="absolute -left-2 top-3 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 md:-top-2 md:left-3" aria-hidden="true" />
                <p className="text-xs font-bold text-emerald-400">{number}</p>
                <h3 className="mt-2 text-sm font-bold text-white">{title}</h3>
                <p className="mt-1 text-xs leading-5 text-slate-400">{description}</p>
                {index < 4 && <span className="sr-only">Then</span>}
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="bg-emerald-700 py-16 text-white sm:py-20">
        <div className="mx-auto flex max-w-7xl flex-col gap-8 px-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <div>
            <p className="text-sm font-semibold text-emerald-100">Your Dhaka rental search, better structured</p>
            <h2 className="mt-2 max-w-3xl text-3xl font-bold leading-tight sm:text-4xl">
              Ready to find a better rental match in Dhaka?
            </h2>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row lg:shrink-0">
            <Link
              href="/register"
              className="inline-flex min-h-12 items-center justify-center rounded-lg bg-white px-6 text-sm font-bold text-emerald-800 hover:bg-emerald-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-emerald-700"
            >
              Create an account
            </Link>
            <Link
              href="/login"
              className="inline-flex min-h-12 items-center justify-center rounded-lg border border-emerald-300 px-6 text-sm font-bold text-white hover:bg-emerald-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            >
              Log in
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="max-w-3xl">
      <p className="text-xs font-bold uppercase text-emerald-700">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">{title}</h2>
      <p className="mt-4 text-base leading-7 text-slate-600">{description}</p>
    </div>
  );
}

function ProcessStep({ number, title, description }: { number: string; title: string; description: string }) {
  return (
    <li className="relative border-l border-slate-300 pl-6 lg:border-l-0 lg:border-t lg:px-8 lg:pt-8 lg:first:pl-0">
      <span className="absolute -left-4 top-0 flex h-8 w-8 items-center justify-center rounded-full bg-slate-950 text-xs font-bold text-white lg:-top-4 lg:left-8 lg:first:left-0">
        {number}
      </span>
      <h3 className="text-lg font-bold text-slate-950">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>
    </li>
  );
}

function RolePanel({
  id,
  label,
  title,
  description,
  points,
  action,
  tone,
}: {
  id: string;
  label: string;
  title: string;
  description: string;
  points: string[];
  action: string;
  tone: "emerald" | "navy";
}) {
  const dark = tone === "navy";
  return (
    <article
      id={id}
      className={[
        "scroll-mt-24 rounded-lg border p-6 sm:p-8",
        dark
          ? "border-slate-800 bg-slate-950 text-white"
          : "border-emerald-200 bg-emerald-50 text-slate-950",
      ].join(" ")}
    >
      <p className={`text-xs font-bold uppercase ${dark ? "text-emerald-400" : "text-emerald-800"}`}>{label}</p>
      <h3 className="mt-3 text-2xl font-bold">{title}</h3>
      <p className={`mt-3 text-sm leading-6 ${dark ? "text-slate-300" : "text-slate-600"}`}>{description}</p>
      <ul className="mt-6 space-y-3">
        {points.map((point) => (
          <li key={point} className="flex items-start gap-3 text-sm">
            <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${dark ? "bg-emerald-500 text-slate-950" : "bg-emerald-700 text-white"}`}>
              <svg viewBox="0 0 20 20" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                <path d="m4 10 4 4 8-8" />
              </svg>
            </span>
            <span className={dark ? "text-slate-200" : "text-slate-700"}>{point}</span>
          </li>
        ))}
      </ul>
      <Link
        href="/register"
        className={[
          "mt-8 inline-flex min-h-12 items-center justify-center rounded-lg px-5 text-sm font-bold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2",
          dark
            ? "bg-white text-slate-950 hover:bg-slate-100 focus-visible:ring-white focus-visible:ring-offset-slate-950"
            : "bg-emerald-700 text-white hover:bg-emerald-800 focus-visible:ring-emerald-600",
        ].join(" ")}
      >
        {action}
      </Link>
    </article>
  );
}

function BenefitIcon({ name }: { name: (typeof benefits)[number]["icon"] }) {
  const common = "h-5 w-5";
  if (name === "pin") {
    return <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>;
  }
  if (name === "wallet") {
    return <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M4 7h15a2 2 0 0 1 2 2v10H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h13"/><path d="M16 12h5v4h-5a2 2 0 1 1 0-4Z"/></svg>;
  }
  if (name === "shield") {
    return <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M12 3 4.5 6v5c0 5 3.2 8.2 7.5 10 4.3-1.8 7.5-5 7.5-10V6L12 3Z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg>;
  }
  return <svg viewBox="0 0 24 24" className={common} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M4 20V10m6 10V4m6 16v-7m4 7H2"/></svg>;
}
