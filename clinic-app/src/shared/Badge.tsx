'use client';

import { ReactNode } from 'react';
import { cn } from '@/shared/utils';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const variantClasses: Record<NonNullable<BadgeProps['variant']>, string> = {
  default: 'bg-slate-100 text-slate-700',
  primary: 'bg-slate-900 text-white',
  success: 'bg-emerald-100 text-emerald-700',
  warning: 'bg-amber-100 text-amber-700',
  error: 'bg-red-100 text-red-700',
  outline: 'border border-slate-300 text-slate-700 bg-transparent',
  ghost: 'text-slate-600 bg-transparent',
};

const sizeClasses: Record<NonNullable<BadgeProps['size']>, string> = {
  sm: 'px-2 py-0.5 text-[11px]',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
};

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium',
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
    >
      {children}
    </span>
  );
}
