export function ProductionBanner() {
  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-ow-accent/10 border border-ow-accent/20">
      <span className="relative flex h-2 w-2">
        <span className="relative inline-flex rounded-full h-2 w-2 bg-ow-accent" />
      </span>
      <span className="text-[11px] font-medium text-ow-accent tracking-wide uppercase">
        Production Mode — Live Gateway
      </span>
    </div>
  );
}
