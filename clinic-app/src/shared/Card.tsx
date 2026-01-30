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
    <div className={`bg-white rounded-lg shadow ${className}`}>
      {title && (
        <div className="px-6 py-4 border-b">
          <h3 className={`text-lg font-medium text-gray-900 ${titleClassName}`}>
            {title}
          </h3>
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  );
}
