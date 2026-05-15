// /projects/clinic-monorepo/clinic-app/src/components/shared/Card.tsx
import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
  titleClassName?: string;
}

export function Card({
  children,
  className = '',
  title,
  titleClassName = '',
}: CardProps) {
  return (
    <div
      className={`rounded-2xl border border-slate-200 bg-white text-slate-900 shadow-sm ${className}`}
    >
      {title && (
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/60">
          <h3 className={`text-lg font-semibold text-slate-900 ${titleClassName}`}>
            {title}
          </h3>
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  );
}
