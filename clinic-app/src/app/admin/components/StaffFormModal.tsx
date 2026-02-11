'use client';

import { useEffect, useMemo, useState } from 'react';
import { UserRole } from '@/shared/enums';
import { StaffResponse } from '@/shared/types';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { Alert } from '@/shared/Alert';

interface StaffFormModalProps {
  isOpen: boolean;
  mode: 'create' | 'edit';
  initialData?: StaffResponse | null;
  onClose: () => void;
  onSubmit: (payload: StaffFormPayload) => Promise<void>;
}

export interface StaffFormPayload {
  full_name: string;
  email: string;
  password?: string;
  role: UserRole;
  is_active?: boolean;
  specialty?: string | null;
  department?: string | null;
  room_label?: string | null;
  availability_status?: string | null;
}

const roleOptions = [
  UserRole.RECEPTION,
  UserRole.DOCTOR,
  UserRole.LAB,
  UserRole.PHARMACY,
  UserRole.CHEW,
  UserRole.MIDWIFE,
];

const availabilityOptions = ['Available', 'On Call', 'Unavailable'];

export function StaffFormModal({
  isOpen,
  mode,
  initialData,
  onClose,
  onSubmit,
}: StaffFormModalProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<StaffFormPayload>({
    full_name: '',
    email: '',
    password: '',
    role: UserRole.RECEPTION,
    is_active: true,
    specialty: '',
    department: '',
    room_label: '',
    availability_status: '',
  });

  const showDoctorFields = useMemo(
    () => form.role === UserRole.DOCTOR,
    [form.role]
  );

  useEffect(() => {
    if (!initialData) {
      setForm({
        full_name: '',
        email: '',
        password: '',
        role: UserRole.RECEPTION,
        is_active: true,
        specialty: '',
        department: '',
        room_label: '',
        availability_status: '',
      });
      setError(null);
      return;
    }

    setForm({
      full_name: initialData.full_name || '',
      email: initialData.email,
      role: initialData.role as UserRole,
      is_active: initialData.is_active,
      specialty: initialData.specialty || '',
      department: initialData.department || '',
      room_label: initialData.room_label || '',
      availability_status: initialData.availability_status || '',
    });
    setError(null);
  }, [initialData, isOpen]);

  const handleChange = (field: keyof StaffFormPayload, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    try {
      setSaving(true);
      setError(null);

      await onSubmit({
        ...form,
        specialty: showDoctorFields ? form.specialty : null,
        department: showDoctorFields ? form.department : null,
        room_label: showDoctorFields ? form.room_label : null,
        availability_status: showDoctorFields ? form.availability_status : null,
      });
      onClose();
    } catch (err: any) {
      console.error('Failed to save staff:', err);
      setError(err.response?.data?.detail || 'Failed to save staff record.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              {mode === 'create' ? 'Add Staff Member' : 'Update Staff Member'}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          {error && <Alert variant="error" className="mb-4">{error}</Alert>}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Full Name"
              value={form.full_name}
              onChange={(e) => handleChange('full_name', e.target.value)}
            />
            <Input
              label="Email"
              value={form.email}
              onChange={(e) => handleChange('email', e.target.value)}
              disabled={mode === 'edit'}
            />
            {mode === 'create' && (
              <Input
                label="Temporary Password"
                type="password"
                value={form.password || ''}
                onChange={(e) => handleChange('password', e.target.value)}
              />
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Role
              </label>
              <select
                value={form.role}
                onChange={(e) => handleChange('role', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={mode === 'edit'}
              >
                {roleOptions.map((role) => (
                  <option key={role} value={role}>
                    {role.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
            {mode === 'edit' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={form.is_active ? 'active' : 'inactive'}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      is_active: e.target.value === 'active',
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="active">Active</option>
                  <option value="inactive">Disabled</option>
                </select>
              </div>
            )}
          </div>

          {showDoctorFields && (
            <div className="mt-6 border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Doctor Profile
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Specialty"
                  value={form.specialty || ''}
                  onChange={(e) => handleChange('specialty', e.target.value)}
                />
                <Input
                  label="Department"
                  value={form.department || ''}
                  onChange={(e) => handleChange('department', e.target.value)}
                />
                <Input
                  label="Room"
                  value={form.room_label || ''}
                  onChange={(e) => handleChange('room_label', e.target.value)}
                />
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Availability
                  </label>
                  <select
                    value={form.availability_status || ''}
                    onChange={(e) =>
                      handleChange('availability_status', e.target.value)
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select availability</option>
                    {availabilityOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-end space-x-3">
            <Button variant="secondary" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSubmit}
              isLoading={saving}
              disabled={saving}
            >
              {mode === 'create' ? 'Create Staff' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
