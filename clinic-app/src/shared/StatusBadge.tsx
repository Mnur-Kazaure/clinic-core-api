import React from 'react';

type StatusVariant = 'success' | 'neutral';

const styles: Record<StatusVariant, string> = {
  success: 'bg-green-100 text-green-700',
  neutral: 'bg-gray-100 text-gray-600',
};

interface StatusBadgeProps {
  label: string;
  variant?: StatusVariant;
}

export function StatusBadge({ label, variant = 'neutral' }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[variant]}`}
    >
      {label}
    </span>
  );
}
