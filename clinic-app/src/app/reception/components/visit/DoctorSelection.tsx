'use client';

import { useEffect, useState } from 'react';
import { userService, Doctor } from '@/domains/user/services/userService';
import { UserRole } from '@/shared/enums';

interface DoctorSelectionProps {
  value?: string;
  onChange: (doctorId: string) => void;
  onSelectDoctor?: (doctor: Doctor | null) => void;
  disabled?: boolean;
  error?: string;
  role?: UserRole | null;
  label?: string;
  serviceLineId?: string;
  includeAllDepartments?: boolean;
  departmentId?: string | null;
}

export function DoctorSelection({
  value,
  onChange,
  onSelectDoctor,
  disabled = false,
  error,
  role = null,
  label = 'Assign Clinician',
  serviceLineId,
  includeAllDepartments = false,
  departmentId = null,
}: DoctorSelectionProps) {
  const [staff, setStaff] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAssignableStaff() {
      try {
        setLoading(true);
        setLoadError(null);
        const data = await userService.listAssignableStaff({
          ...(serviceLineId ? { service_line_id: serviceLineId } : {}),
          ...(role ? { role } : {}),
          include_all_departments: includeAllDepartments,
          ...(departmentId ? { department_id: departmentId } : {}),
        });
        setStaff(data);
      } catch (err: unknown) {
        console.error('Failed to load assignable staff:', err);
        setLoadError('Unable to load assignable staff. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    loadAssignableStaff();
  }, [serviceLineId, role, includeAllDepartments, departmentId]);

  const filteredStaff = role
    ? staff.filter((member) => member.role === role)
    : staff;
  const roleLabel =
    role === UserRole.CHEW
      ? 'CHEW'
      : role === UserRole.MIDWIFE
      ? 'midwife'
      : role === UserRole.DOCTOR
      ? 'doctor'
      : 'clinician';

  useEffect(() => {
    if (!value) return;
    const stillAvailable = filteredStaff.some((member) => member.id === value);
    if (!stillAvailable) {
      onChange('');
      onSelectDoctor?.(null);
    }
  }, [filteredStaff, value, onChange, onSelectDoctor]);

  if (loading) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
        <div className="animate-pulse h-10 bg-gray-200 rounded-md"></div>
        <p className="text-sm text-gray-500">Loading assignable staff...</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{loadError}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 text-sm text-red-700 hover:text-red-800"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (filteredStaff.length === 0) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-700">
            No active {roleLabel} found in this clinic. Contact administrator.
          </p>
        </div>
      </div>
    );
  }

  const formatStaffLabel = (member: Doctor) => {
    const name = member.full_name || 'Unnamed Staff';
    const specialty = member.specialty ? ` • ${member.specialty}` : '';
    const department = member.department ? ` (${member.department})` : '';
    return `${name}${specialty}${department}`;
  };

  const selectedStaff =
    filteredStaff.find((member) => member.id === value) || null;

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        {label}
      </label>
      <select
        value={value || ''}
        onChange={(e) => {
          const doctorId = e.target.value;
          onChange(doctorId);
          if (onSelectDoctor) {
            const selected = filteredStaff.find((member) => member.id === doctorId);
            onSelectDoctor(selected || null);
          }
        }}
        disabled={disabled}
        className={`
          w-full px-3 py-2 border rounded-md shadow-sm
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          ${error ? 'border-red-300' : 'border-gray-300'}
          ${disabled ? 'bg-gray-100 cursor-not-allowed' : ''}
        `}
      >
        <option value="">Select a {roleLabel}</option>
        {filteredStaff.map((member) => (
          <option key={member.id} value={member.id}>
            {formatStaffLabel(member)}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {selectedStaff && (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
          <p className="font-semibold text-slate-900">
            {selectedStaff.full_name || 'Unnamed Staff'}
          </p>
          {selectedStaff.specialty && (
            <p>{selectedStaff.specialty}</p>
          )}
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
            {selectedStaff.department && (
              <span>Dept: {selectedStaff.department}</span>
            )}
            {selectedStaff.room_label && (
              <span>Room: {selectedStaff.room_label}</span>
            )}
            {selectedStaff.availability_status && (
              <span>Status: {selectedStaff.availability_status}</span>
            )}
          </div>
        </div>
      )}
      <p className="text-xs text-gray-500">
        {filteredStaff.length} of {staff.length} active assignable staff shown
      </p>
    </div>
  );
}
