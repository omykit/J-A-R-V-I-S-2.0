import {
  LayoutDashboard,
  Zap,
  Brain,
  Settings,
} from "lucide-react";

export default function LeftRail() {
  const items = [
    LayoutDashboard,
    Zap,
    Brain,
    Settings,
  ];

  return (
    <div className="absolute left-5 top-1/2 -translate-y-1/2 z-30 flex flex-col gap-4">

      {items.map((Icon, index) => (
        <button
          key={index}
          className="w-10 h-10 flex items-center justify-center rounded-md
          border border-cyan-400/10
          bg-[#06101a]/60
          text-slate-500
          hover:text-cyan-300
          hover:border-cyan-400/40
          transition-all"
        >
          <Icon size={17} />
        </button>
      ))}

    </div>
  );
}