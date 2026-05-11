'use client';

import { ReactNode } from 'react';
import { LAB_WORKSPACE_THEME } from '@/domains/lab/constants/labWorkspaceTheme';
import { Card } from '@/shared/Card';
import { HOSPITAL_NAME } from '@/shared/constants/branding';

interface DashboardHeroProps {
  title: string;
  subtitle?: string;
  workspaceLabel?: string;
  monogram?: string;
  rightSlot?: ReactNode;
  actionsSlot?: ReactNode;
  variant?: 'brand-gradient' | 'calm-light' | 'calm-brand';
  accentLabel?: string;
}

export function DashboardHero({
  title,
  subtitle = HOSPITAL_NAME,
  workspaceLabel,
  monogram = 'K',
  rightSlot,
  actionsSlot,
  variant = 'brand-gradient',
  accentLabel,
}: DashboardHeroProps) {
  const isCalmLight = variant === 'calm-light';
  const isCalmBrand = variant === 'calm-brand';
  const isCalmVariant = isCalmLight || isCalmBrand;
  const heroPaddingClass = isCalmBrand ? 'p-0' : 'p-6';

  return (
    <Card
      className={`overflow-hidden shadow-md ${
        isCalmVariant
          ? isCalmBrand
            ? 'border border-[#D7E6F8] bg-[#FEFEFE] shadow-[0_20px_44px_rgba(30,75,140,0.12)]'
            : 'border border-[#E2E8F0] bg-[#FEFEFE]'
          : 'border-0'
      }`}
    >
      <div
        className={`relative rounded-xl ${heroPaddingClass} ${
          isCalmVariant ? 'text-[#0F172A]' : 'text-white'
        }`}
        style={
          isCalmVariant
            ? {
                background: isCalmBrand
                  ? LAB_WORKSPACE_THEME.surface
                  : '#FEFEFE',
                borderBottom: isCalmBrand
                  ? `1px solid ${LAB_WORKSPACE_THEME.border}`
                  : `1px solid ${LAB_WORKSPACE_THEME.divider}`,
              }
            : {
                background: 'linear-gradient(120deg, #1E3A8A 0%, #0F766E 100%)',
              }
        }
      >
        {isCalmBrand ? (
          <>
            <div
              aria-hidden
              className="pointer-events-none absolute inset-y-0 left-0 w-28 rounded-l-xl"
              style={{
                background: `linear-gradient(180deg, ${LAB_WORKSPACE_THEME.primary} 0%, #2563A8 56%, ${LAB_WORKSPACE_THEME.accent} 100%)`,
              }}
            />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-y-0 left-0 w-[18rem]"
              style={{
                background:
                  'linear-gradient(92deg, rgba(30,75,140,0.28) 0%, rgba(37,99,168,0.16) 38%, rgba(63,163,207,0.08) 62%, rgba(255,255,255,0) 100%)',
              }}
            />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-y-6 left-4 w-[7.5rem] rounded-[1.75rem]"
              style={{
                background:
                  'linear-gradient(180deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.03) 100%)',
                  border: '1px solid rgba(255,255,255,0.18)',
                  boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.25)',
              }}
            />
            <div
              aria-hidden
              className="pointer-events-none absolute left-8 top-8 h-28 w-28 rounded-full"
              style={{
                background:
                  'radial-gradient(circle, rgba(63,163,207,0.28) 0%, rgba(63,163,207,0) 72%)',
              }}
            />
            <div
              aria-hidden
              className="pointer-events-none absolute right-6 top-0 h-24 w-48"
              style={{
                background:
                  'linear-gradient(180deg, rgba(63,163,207,0.08) 0%, rgba(63,163,207,0) 100%)',
              }}
            />
          </>
        ) : null}

        <div
          className={`relative z-10 flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between ${
            isCalmBrand ? 'px-7 py-6' : ''
          }`}
        >
          <div className="flex items-center gap-4">
            <div
              className={`h-12 w-12 rounded-xl text-center text-xl font-bold leading-[3rem] ${
                isCalmVariant
                  ? isCalmBrand
                    ? 'border border-white/30 text-white shadow-[0_18px_32px_rgba(15,23,42,0.2)]'
                    : 'bg-[#EAF4FB] text-[#1E4B8C]'
                  : 'bg-white/20 text-white'
              }`}
              style={
                isCalmBrand
                  ? {
                      background:
                        `linear-gradient(145deg, rgba(30,75,140,0.96) 0%, rgba(37,99,168,0.92) 58%, ${LAB_WORKSPACE_THEME.accent} 100%)`,
                    }
                  : undefined
              }
            >
              {monogram}
            </div>
            <div>
              {isCalmVariant && accentLabel ? (
                <span
                  className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${
                    isCalmBrand
                      ? 'border bg-white shadow-[0_8px_18px_rgba(30,75,140,0.08)]'
                      : 'bg-[#EAF4FB] text-[#1E4B8C]'
                  }`}
                  style={
                    isCalmBrand
                      ? {
                          borderColor: LAB_WORKSPACE_THEME.badgeBorder,
                          color: LAB_WORKSPACE_THEME.badgeText,
                        }
                      : undefined
                  }
                >
                  {accentLabel}
                </span>
              ) : null}
              <h1 className="text-2xl font-semibold">{title}</h1>
              <p className={`text-sm ${isCalmVariant ? 'text-[#5A666D]' : 'text-blue-100'}`}>
                {subtitle}
              </p>
              {workspaceLabel ? (
                <p className={`text-sm ${isCalmVariant ? 'text-[#5A666D]' : 'text-blue-100'}`}>
                  {workspaceLabel}
                </p>
              ) : null}
            </div>
          </div>
          {rightSlot ? (
            <div
              className={`grid gap-1 text-sm xl:text-right ${
                isCalmVariant ? 'text-[#5A666D]' : ''
              }`}
              style={
                isCalmBrand
                  ? {
                      padding: '0.8rem 1rem',
                      borderRadius: '1rem',
                      border: `1px solid ${LAB_WORKSPACE_THEME.badgeBorder}`,
                      background:
                        'linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(244,249,255,0.98) 100%)',
                      boxShadow: '0 14px 28px rgba(30,75,140,0.08)',
                    }
                  : undefined
              }
            >
              {rightSlot}
            </div>
          ) : null}
        </div>

        {actionsSlot ? (
          <div className="relative z-10 mt-4 flex flex-wrap items-center gap-2">
            {actionsSlot}
          </div>
        ) : null}
      </div>
    </Card>
  );
}
