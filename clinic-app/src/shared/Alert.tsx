import React from 'react';

type AlertVariant = 'info' | 'success' | 'warning' | 'error';

const variantStyles: Record<AlertVariant, string> = {
  info: 'bg-blue-50 border-blue-200 text-blue-700',
  success: 'bg-green-50 border-green-200 text-green-700',
  warning: 'bg-yellow-50 border-yellow-200 text-yellow-700',
  error: 'bg-red-50 border-red-200 text-red-700',
};

interface AlertProps {
  variant?: AlertVariant;
  children: React.ReactNode;
  className?: string;
}

export function Alert({
  variant = 'info',
  children,
  className = '',
}: AlertProps) {
  return (
    <div
      role="alert"
      className={`rounded-md border p-3 text-sm ${variantStyles[variant]} ${className}`}
    >
      {children}
    </div>
  );
}
