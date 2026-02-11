'use client';

import { useEffect, useMemo, useState } from 'react';
import { clinicService } from '@/domains/clinic/services/clinicService';
import { ClinicProfileResponse } from '@/shared/types';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { Alert } from '@/shared/Alert';

const DEFAULT_FEE_NAIRA = 1000;
const DEFAULT_FEE_MINOR = DEFAULT_FEE_NAIRA * 100;

const FEE_OPTIONS = [
  { label: '₦1,000', value: 1000 },
  { label: '₦2,000', value: 2000 },
  { label: '₦5,000', value: 5000 },
  { label: '₦10,000', value: 10000 },
  { label: '₦20,000', value: 20000 },
  { label: 'Other', value: 'OTHER' as const },
];

export function ClinicSettingsForm() {
  const [profile, setProfile] = useState<ClinicProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [feeRequired, setFeeRequired] = useState(true);
  const [feeOption, setFeeOption] = useState<string>('1000');
  const [customFeeNaira, setCustomFeeNaira] = useState<string>('');
  const [monthlyTargetNaira, setMonthlyTargetNaira] = useState<string>('');

  useEffect(() => {
    async function loadProfile() {
      try {
        setLoading(true);
        const data = await clinicService.getProfile();
        setProfile(data);
        const minor = data.registration_fee_minor ?? DEFAULT_FEE_MINOR;
        const naira = Math.round(minor / 100);
        const option = FEE_OPTIONS.find((item) => item.value === naira);
        setFeeOption(option ? String(option.value) : 'OTHER');
        setCustomFeeNaira(option ? '' : String(naira));
        setFeeRequired(data.registration_fee_required ?? true);
        if (typeof data.monthly_revenue_target_minor === 'number') {
          setMonthlyTargetNaira(
            String(Math.round(data.monthly_revenue_target_minor / 100))
          );
        } else {
          setMonthlyTargetNaira('');
        }
      } catch {
        setError('Unable to load clinic settings.');
      } finally {
        setLoading(false);
      }
    }

    loadProfile();
  }, []);

  const currencyLabel = profile?.billing_currency || 'NGN';

  const computedFeeMinor = useMemo(() => {
    if (feeOption === 'OTHER') {
      const parsed = Number(customFeeNaira);
      return Number.isFinite(parsed) ? Math.max(parsed, 0) * 100 : 0;
    }
    const selected = Number(feeOption);
    return Number.isFinite(selected) ? selected * 100 : 0;
  }, [feeOption, customFeeNaira]);

  const handleSave = async () => {
    try {
      setError(null);
      setSuccess(null);
      if (feeRequired && computedFeeMinor <= 0) {
        setError('Registration fee must be greater than 0 when required.');
        return;
      }
      setSaving(true);
      const payload = {
        registration_fee_required: feeRequired,
        registration_fee_minor: feeRequired ? computedFeeMinor : 0,
        monthly_revenue_target_minor: monthlyTargetNaira
          ? Number(monthlyTargetNaira) * 100
          : 0,
      };
      const updated = await clinicService.updateProfile(payload);
      setProfile(updated);
      setSuccess('Clinic settings updated.');
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || 'Failed to update settings.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card title="Clinic Settings" titleClassName="text-slate-900">
        <div className="space-y-4">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Clinic Settings" titleClassName="text-slate-900">
      <div className="space-y-6">
        {error && <Alert variant="error">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-800">Registration Fee</h3>
              <p className="text-xs text-slate-500">
                Fee required before patient registration.
              </p>
            </div>
            <span className="text-xs font-medium text-slate-600">
              Currency: {currencyLabel}
            </span>
          </div>

          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Fee amount (Naira)
              </label>
              <select
                value={feeOption}
                onChange={(e) => setFeeOption(e.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {FEE_OPTIONS.map((option) => (
                  <option key={option.label} value={String(option.value)}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Input
                label="Custom fee (Naira)"
                type="number"
                value={customFeeNaira}
                onChange={(e) => setCustomFeeNaira(e.target.value)}
                disabled={feeOption !== 'OTHER'}
                placeholder="Enter fee amount"
              />
            </div>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <input
              id="registration_fee_required_setting"
              type="checkbox"
              checked={feeRequired}
              onChange={(e) => setFeeRequired(e.target.checked)}
              className="h-4 w-4 text-blue-600"
            />
            <label
              htmlFor="registration_fee_required_setting"
              className="text-sm text-gray-700"
            >
              Require registration fee before patient is created
            </label>
          </div>

          <p className="mt-2 text-xs text-slate-500">
            Default is ₦{DEFAULT_FEE_NAIRA.toLocaleString()} ({DEFAULT_FEE_MINOR} kobo).
          </p>
        </div>

        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <h3 className="text-sm font-semibold text-slate-800">Monthly Revenue Target</h3>
          <p className="text-xs text-slate-500">
            Used for payment oversight progress tracking.
          </p>
          <div className="mt-4">
            <Input
              label="Target amount (Naira)"
              type="number"
              value={monthlyTargetNaira}
              onChange={(e) => setMonthlyTargetNaira(e.target.value)}
              placeholder="e.g. 8000000"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button
            variant="primary"
            onClick={handleSave}
            isLoading={saving}
            disabled={saving}
          >
            Save Settings
          </Button>
        </div>
      </div>
    </Card>
  );
}
