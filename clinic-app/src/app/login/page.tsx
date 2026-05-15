'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authService } from '@/domains/auth/services/authService';
import { HOSPITAL_NAME } from '@/shared/constants/branding';

function EyeIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M17.94 17.94A10.94 10.94 0 0 1 12 19C5 19 1 12 1 12a21.89 21.89 0 0 1 5.06-6.94" />
      <path d="M9.53 9.53A3.5 3.5 0 0 0 12 15.5a3.5 3.5 0 0 0 2.47-.97" />
      <path d="M14.47 14.47 9.53 9.53" />
      <path d="M20.94 13.94A21.87 21.87 0 0 0 23 12s-4-7-11-7a10.94 10.94 0 0 0-4.94 1.18" />
      <path d="M1 1l22 22" />
    </svg>
  );
}

const CAPABILITIES = [
  'Clinical Operations',
  'Pharmacy Management',
  'Billing & Revenue',
  'Hospital Administration',
] as const;

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [keepSignedIn, setKeepSignedIn] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login({ email, password });
      router.push('/confirm-access');
    } catch {
      setError('Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-100 text-slate-900">
      <div
        className="absolute inset-0 hidden bg-cover bg-center md:block"
        style={{
          backgroundImage:
            "linear-gradient(135deg, rgba(15,108,116,0.55), rgba(11,31,52,0.55)), url('/assets/auth/login-bg-desktop.webp')",
        }}
      />
      <div
        className="absolute inset-0 bg-cover bg-center md:hidden"
        style={{
          backgroundImage:
            "linear-gradient(135deg, rgba(15,108,116,0.55), rgba(11,31,52,0.55)), url('/assets/auth/login-bg-mobile.webp')",
        }}
      />

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(31,143,168,0.16),transparent_35%),radial-gradient(circle_at_bottom_right,rgba(15,108,116,0.24),transparent_30%),linear-gradient(135deg,#0b1f34,#123c45_45%,#0f6c74_100%)]" />
      <div className="absolute inset-0 bg-black/15" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(7,12,20,0.52),rgba(7,12,20,0.18),rgba(7,12,20,0.42))]" />

      <div className="relative z-10 min-h-screen px-4 py-6 sm:px-6 lg:px-10">
        <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-7xl items-center lg:grid lg:grid-cols-[1.1fr_0.9fr] lg:gap-10">
          <section className="hidden text-white lg:block">
            <div className="max-w-xl space-y-6">
              <div className="inline-flex items-center gap-3 rounded-full border border-white/20 bg-white/10 px-4 py-2 backdrop-blur-sm">
                <div className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="text-sm font-medium tracking-wide text-white/90">
                  {HOSPITAL_NAME} • HIS Access
                </span>
              </div>

              <div className="space-y-4">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-cyan-100/80">
                  Hospital Information System
                </p>
                <h1 className="text-5xl font-semibold leading-tight">
                  Entering the digital gateway of {HOSPITAL_NAME}
                </h1>
                <p className="max-w-lg text-lg leading-8 text-slate-200/90">
                  Secure access to pharmacy, billing, records, clinical operations,
                  and hospital administration.
                </p>
              </div>

              <div className="grid max-w-lg grid-cols-2 gap-4 pt-4">
                {CAPABILITIES.map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-white/15 bg-white/10 px-4 py-4 backdrop-blur-md"
                  >
                    <div className="text-sm font-medium text-white/90">{item}</div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="mx-auto w-full max-w-md lg:justify-self-end">
            <div className="rounded-[28px] border border-white/40 bg-white/90 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.22)] backdrop-blur-xl sm:p-8">
              <div className="mb-8 space-y-3 text-center">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,#0F6C74,#1F8FA8)] text-xl font-bold text-white shadow-lg">
                  KSH
                </div>
                <div className="space-y-2">
                  <h2 className="text-4xl font-semibold tracking-tight text-slate-950">
                    {HOSPITAL_NAME}
                  </h2>
                  <p className="text-sm font-medium text-slate-600">
                    Hospital Information System Access Portal
                  </p>
                </div>
              </div>

              <form className="space-y-5" onSubmit={handleSubmit}>
                {error ? (
                  <div
                    className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-center text-sm text-red-700"
                    role="alert"
                  >
                    {error}
                  </div>
                ) : null}

                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-medium text-slate-700">
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={loading}
                    placeholder="Enter your hospital email"
                    className="h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 text-sm outline-none ring-0 transition focus:border-[#0F6C74] focus:shadow-[0_0_0_4px_rgba(15,108,116,0.10)] disabled:cursor-not-allowed disabled:bg-slate-100"
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="password" className="text-sm font-medium text-slate-700">
                    Password
                  </label>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      disabled={loading}
                      placeholder="Enter your password"
                      className="h-12 w-full rounded-2xl border border-slate-200 bg-white px-4 pr-12 text-sm outline-none ring-0 transition focus:border-[#0F6C74] focus:shadow-[0_0_0_4px_rgba(15,108,116,0.10)] disabled:cursor-not-allowed disabled:bg-slate-100"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((prev) => !prev)}
                      className="absolute inset-y-0 right-3 my-auto flex h-8 w-8 items-center justify-center rounded-full text-slate-500 transition hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#0F6C74] focus:ring-offset-1 disabled:cursor-not-allowed disabled:text-slate-300"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      aria-pressed={showPassword}
                      disabled={loading}
                    >
                      {showPassword ? <EyeOffIcon /> : <EyeIcon />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <label className="flex items-center gap-2 text-slate-600">
                    <input
                      type="checkbox"
                      checked={keepSignedIn}
                      onChange={(event) => setKeepSignedIn(event.target.checked)}
                      className="rounded border-slate-300 text-[#0F6C74] focus:ring-[#0F6C74]"
                      disabled={loading}
                    />
                    Keep me signed in
                  </label>
                  <button
                    type="button"
                    className="font-medium text-[#0F6C74] hover:text-[#0B4F59]"
                    disabled={loading}
                  >
                    Need help?
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="h-12 w-full rounded-2xl bg-[linear-gradient(135deg,#0F6C74,#1F8FA8)] text-sm font-semibold text-white shadow-lg transition hover:translate-y-[-1px] hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-[#0F6C74] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {loading ? 'Signing in securely...' : 'Sign in securely'}
                </button>
              </form>

              <div className="mt-6 rounded-2xl border border-slate-200/80 bg-slate-50 px-4 py-3 text-center text-xs text-slate-600">
                Authorized hospital staff only • Secure institutional access
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
