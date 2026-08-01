import type { ReactNode } from "react";

interface PreferenceSectionProps {
  number: number;
  title: string;
  description: string;
  children: ReactNode;
}

export default function PreferenceSection({
  number,
  title,
  description,
  children,
}: PreferenceSectionProps) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex gap-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-800">
          {number}
        </span>
        <div>
          <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
          <p className="mt-1 text-sm text-slate-600">{description}</p>
        </div>
      </div>
      <div className="mt-6">{children}</div>
    </section>
  );
}
