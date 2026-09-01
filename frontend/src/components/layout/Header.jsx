export default function Header() {
  return (
    <header className="absolute top-0 left-0 right-0 z-30 flex items-start justify-between px-8 py-6">

      <div>
        <div className="font-mono text-lg tracking-[0.35em] text-cyan-50">
          J.A.R.V.I.S
        </div>

        <div className="mt-1 text-[9px] tracking-[0.16em] text-slate-500">
          JUST A RATHER VERY INTELLIGENT SYSTEM
        </div>
      </div>

      <div className="flex items-center gap-6">

        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(0,207,239,0.9)]" />

          <span className="text-[10px] tracking-[0.22em] text-cyan-400">
            SYSTEM ONLINE
          </span>
        </div>

      </div>
c  
    </header>
  );
}