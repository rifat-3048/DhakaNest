interface PrioritySelectorProps {
  label: string;
  description: string;
  value: number;
  onChange: (value: number) => void;
}

export default function PrioritySelector({
  label,
  description,
  value,
  onChange,
}: PrioritySelectorProps) {
  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-900">{label}</p>
          <p className="mt-1 text-xs text-slate-500">{description}</p>
        </div>
        <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-bold text-emerald-800">
          {value}/5
        </span>
      </div>
      <input
        type="range"
        min={1}
        max={5}
        step={1}
        value={value}
        aria-label={`${label} priority`}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-4 w-full accent-emerald-700"
      />
      <div className="mt-1 flex justify-between text-xs text-slate-400">
        <span>Low priority</span>
        <span>Essential</span>
      </div>
    </div>
  );
}
