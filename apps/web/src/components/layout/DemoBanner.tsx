export function DemoBanner() {
  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-ow-approval/10 border border-ow-approval/20">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ow-approval opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-ow-approval" />
      </span>
      <span className="text-[11px] font-medium text-ow-approval tracking-wide uppercase">
        Demo Mode — Synthetic Data
      </span>
    </div>
  );
}
