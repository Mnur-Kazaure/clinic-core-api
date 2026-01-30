import { ReactNode } from 'react';

interface TooltipProps {
  content: string;
  children: ReactNode;
  widthClassName?: string;
}

export function Tooltip({
  content,
  children,
  widthClassName = 'w-60',
}: TooltipProps) {
  return (
    <div className="relative inline-block group">
      {children}
      <div
        role="tooltip"
        className={`pointer-events-none absolute left-1/2 top-0 z-10 ${widthClassName} -translate-x-1/2 -translate-y-full rounded-xl bg-[#1F2937]/60 px-4 py-3 text-sm font-medium text-white opacity-0 shadow-xl backdrop-blur transition-opacity duration-150 delay-300 group-hover:opacity-100`}
      >
        {content}
        <span className="absolute left-1/2 top-full h-3 w-3 -translate-x-1/2 -translate-y-1/2 rotate-45 bg-[#1F2937]/60"></span>
      </div>
    </div>
  );
}
