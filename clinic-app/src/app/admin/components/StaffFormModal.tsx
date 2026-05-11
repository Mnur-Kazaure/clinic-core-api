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
  labUnitOptions: LabUnitOption[];
  onClose: () => void;
  onSubmit: (payload: StaffFormPayload) => Promise<void>;
}

export interface LabUnitOption {
  id: string;
  name: string;
  path_label?: string;
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
  allowed_lab_unit_ids?: string[];
  default_lab_unit_id?: string | null;
}

const roleOptions = [
  UserRole.RECEPTION,
  UserRole.CASHIER,
  UserRole.ACCOUNTANT,
  UserRole.CMD,
  UserRole.DOCTOR,
  UserRole.LAB,
  UserRole.LAB_TECH,
  UserRole.LAB_SCIENTIST,
  UserRole.LAB_SUPERVISOR,
  UserRole.LAB_MANAGER,
  UserRole.PHARMACY,
  UserRole.PHARMACY_HOD,
  UserRole.PHARMACY_STORE_OFFICER,
  UserRole.CHEW,
  UserRole.MIDWIFE,
];

const roleLabels: Partial<Record<UserRole, string>> = {
  [UserRole.LAB]: 'LAB (Legacy)',
  [UserRole.LAB_MANAGER]: 'Medical Laboratory HOD',
  [UserRole.CMD]: 'Chief Medical Director (CMD)',
  [UserRole.PHARMACY_HOD]: 'Pharmacy HOD',
  [UserRole.PHARMACY_STORE_OFFICER]: 'Pharmacy Store Officer',
};

const availabilityOptions = ['Available', 'On Call', 'Unavailable'];

export function StaffFormModal({
  isOpen,
  mode,
  initialData,
  labUnitOptions,
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
      allowed_lab_unit_ids: [],
      default_lab_unit_id: null,
    });

  const showDoctorFields = useMemo(
    () => form.role === UserRole.DOCTOR,
    [form.role]
  );
  const isLabOperationalRole = useMemo(
    () =>
      [
        UserRole.LAB,
        UserRole.LAB_TECH,
        UserRole.LAB_SCIENTIST,
        UserRole.LAB_SUPERVISOR,
      ].includes(form.role),
    [form.role]
  );
  const isLabManagerRole = useMemo(
    () => form.role === UserRole.LAB_MANAGER,
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
        allowed_lab_unit_ids: [],
        default_lab_unit_id: null,
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
      allowed_lab_unit_ids: initialData.allowed_lab_units?.map((unit) => unit.id) || [],
      default_lab_unit_id: initialData.default_lab_unit_id || null,
    });
    setError(null);
  }, [initialData, isOpen]);

  const handleChange = (field: keyof StaffFormPayload, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleLabUnitToggle = (unitId: string, checked: boolean) => {
    setForm((prev) => {
      const selected = new Set(prev.allowed_lab_unit_ids || []);
      if (checked) {
        selected.add(unitId);
      } else {
        selected.delete(unitId);
      }
      const nextAllowed = Array.from(selected);
      const nextDefault =
        prev.default_lab_unit_id && nextAllowed.includes(prev.default_lab_unit_id)
          ? prev.default_lab_unit_id
          : nextAllowed[0] || null;
      return {
        ...prev,
        allowed_lab_unit_ids: nextAllowed,
        default_lab_unit_id: nextDefault,
      };
    });
  };

  const handleSubmit = async () => {
    try {
      setSaving(true);
      setError(null);

      if (isLabOperationalRole && (form.allowed_lab_unit_ids || []).length === 0) {
        setError('Select at least one allowed lab unit for operational lab staff.');
        return;
      }

      await onSubmit({
        ...form,
        specialty: showDoctorFields ? form.specialty : null,
        department: showDoctorFields ? form.department : null,
        room_label: showDoctorFields ? form.room_label : null,
        availability_status: showDoctorFields ? form.availability_status : null,
        allowed_lab_unit_ids: isLabOperationalRole ? form.allowed_lab_unit_ids : [],
        default_lab_unit_id: isLabOperationalRole ? form.default_lab_unit_id : null,
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
              >
                {roleOptions.map((role) => (
                  <option key={role} value={role}>
                    {roleLabels[role] || role.replaceAll('_', ' ')}
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

          {(isLabOperationalRole || isLabManagerRole) && (
            <div className="mt-6 border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">
                Laboratory Workforce Access
              </h3>
              {isLabManagerRole ? (
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  Lab manager accounts route to the separate HOD/manager workspace and
                  oversee unit activity without a technician queue assignment.
                </div>
              ) : labUnitOptions.length === 0 ? (
                <Alert variant="error">
                  No laboratory units are currently available. Configure Medical
                  Laboratory units in Service Lines first.
                </Alert>
              ) : (
                <div className="space-y-4">
                  <div>
                    <p className="mb-2 text-sm font-medium text-gray-700">
                      Allowed Lab Units
                    </p>
                    <div className="max-h-52 space-y-2 overflow-y-auto rounded-lg border border-slate-200 p-3">
                      {labUnitOptions.map((unit) => {
                        const checked = (form.allowed_lab_unit_ids || []).includes(unit.id);
                        return (
                          <label
                            key={unit.id}
                            className="flex items-start gap-3 rounded-md border border-slate-100 px-3 py-2 hover:bg-slate-50"
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={(event) =>
                                handleLabUnitToggle(unit.id, event.target.checked)
                              }
                              className="mt-1 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="text-sm text-slate-700">
                              <span className="block font-medium">{unit.name}</span>
                              {unit.path_label && (
                                <span className="block text-xs text-slate-500">
                                  {unit.path_label}
                                </span>
                              )}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Default Lab Unit
                    </label>
                    <select
                      value={form.default_lab_unit_id || ''}
                      onChange={(event) =>
                        setForm((prev) => ({
                          ...prev,
                          default_lab_unit_id: event.target.value || null,
                        }))
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {(form.allowed_lab_unit_ids || []).length === 0 ? (
                        <option value="">Select allowed units first</option>
                      ) : (
                        (form.allowed_lab_unit_ids || []).map((unitId) => {
                          const option = labUnitOptions.find((unit) => unit.id === unitId);
                          return (
                            <option key={unitId} value={unitId}>
                              {option?.name || unitId}
                            </option>
                          );
                        })
                      )}
                    </select>
                  </div>
                </div>
              )}
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
