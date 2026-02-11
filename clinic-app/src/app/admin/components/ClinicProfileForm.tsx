// clinic-app/src/app/admin/components/ClinicProfileForm.tsx
'use client';

import { useEffect, useState } from 'react';
import { clinicService, ClinicProfileUpdateRequest } from '@/domains/clinic/services/clinicService';
import { ClinicProfileResponse } from '@/shared/types';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { Alert } from '@/shared/Alert';

const emptyProfile: ClinicProfileResponse = {
  id: '',
  name: '',
  logo_url: null,
  address: null,
  phone: null,
  email: null,
  timezone: null,
  description: null,
};

export function ClinicProfileForm() {
  const [profile, setProfile] = useState<ClinicProfileResponse>(emptyProfile);
  const [formState, setFormState] = useState<ClinicProfileUpdateRequest>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function loadProfile() {
      try {
        setLoading(true);
        setError(null);
        const data = await clinicService.getProfile();
        setProfile(data);
        setFormState({
          name: data.name,
          logo_url: data.logo_url || '',
          address: data.address || '',
          phone: data.phone || '',
          email: data.email || '',
          timezone: data.timezone || '',
          description: data.description || '',
        });
      } catch (err: unknown) {
        console.error('Failed to load clinic profile:', err);
        setError('Unable to load clinic profile.');
      } finally {
        setLoading(false);
      }
    }

    loadProfile();
  }, []);

  const handleChange = (field: keyof ClinicProfileUpdateRequest, value: string) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      const payload: ClinicProfileUpdateRequest = {};
      const setIf = (
        key: keyof ClinicProfileUpdateRequest,
        value: ClinicProfileUpdateRequest[keyof ClinicProfileUpdateRequest]
      ) => {
        if (value === undefined || value === null) return;
        if (typeof value === 'string' && value.trim() === '') return;
        payload[key] = typeof value === 'string' ? value.trim() : value;
      };

      setIf('name', formState.name);
      setIf('logo_url', formState.logo_url);
      setIf('address', formState.address);
      setIf('phone', formState.phone);
      setIf('email', formState.email);
      setIf('timezone', formState.timezone);
      setIf('description', formState.description);

      const updated = await clinicService.updateProfile(payload);
      setProfile(updated);
      setSuccess('Clinic profile updated successfully.');
    } catch (err: unknown) {
      console.error('Failed to update clinic profile:', err);
      const detail =
        typeof err === 'object' && err && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined;
      setError(detail || 'Failed to update clinic profile.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card title="Clinic Profile" titleClassName="text-slate-900">
        <div className="space-y-4">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Clinic Profile" titleClassName="text-slate-900">
      <div className="space-y-6">
        {error && <Alert variant="error">{error}</Alert>}
        {success && <Alert variant="success">{success}</Alert>}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="Clinic Name"
            value={formState.name || ''}
            onChange={(e) => handleChange('name', e.target.value)}
          />
          <Input
            label="Clinic Email"
            value={formState.email || ''}
            onChange={(e) => handleChange('email', e.target.value)}
          />
          <Input
            label="Phone"
            value={formState.phone || ''}
            onChange={(e) => handleChange('phone', e.target.value)}
          />
          <Input
            label="Timezone"
            value={formState.timezone || ''}
            onChange={(e) => handleChange('timezone', e.target.value)}
            placeholder="Africa/Lagos"
          />
          <Input
            label="Logo URL"
            value={formState.logo_url || ''}
            onChange={(e) => handleChange('logo_url', e.target.value)}
            placeholder="https://..."
          />
          <Input
            label="Address"
            value={formState.address || ''}
            onChange={(e) => handleChange('address', e.target.value)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={formState.description || ''}
            onChange={(e) => handleChange('description', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px]"
          />
        </div>

        {profile.logo_url && (
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <span className="font-medium text-gray-900">Current Logo:</span>
            <a
              href={profile.logo_url}
              className="text-blue-600 hover:text-blue-700"
              target="_blank"
              rel="noreferrer"
            >
              View logo
            </a>
          </div>
        )}

        <div className="flex justify-end">
          <Button
            variant="primary"
            onClick={handleSave}
            isLoading={saving}
            disabled={saving}
          >
            Save Changes
          </Button>
        </div>
      </div>
    </Card>
  );
}
