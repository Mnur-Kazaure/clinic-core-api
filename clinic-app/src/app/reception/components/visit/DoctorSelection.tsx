'use client';

import { useEffect, useState } from 'react';
import { userService, Doctor } from '@/domains/user/services/userService';

interface DoctorSelectionProps {
  value?: string;
  onChange: (doctorId: string) => void;
  onSelectDoctor?: (doctor: Doctor | null) => void;
  disabled?: boolean;
  error?: string;
}

export function DoctorSelection({
  value,
  onChange,
  onSelectDoctor,
  disabled = false,
  error,
}: DoctorSelectionProps) {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDoctors() {
      try {
        setLoading(true);
        setLoadError(null);
        const data = await userService.listDoctors();
        setDoctors(data);
      } catch (err: any) {
        console.error('Failed to load doctors:', err);
        setLoadError('Unable to load doctors. Please try again.');
      } finally {
        setLoading(false);
      }
    }

    loadDoctors();
  }, []);

  if (loading) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Assign Doctor
        </label>
        <div className="animate-pulse h-10 bg-gray-200 rounded-md"></div>
        <p className="text-sm text-gray-500">Loading available doctors...</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Assign Doctor
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

  if (doctors.length === 0) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700">
          Assign Doctor
        </label>
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-700">
            No doctors available in this clinic. Contact administrator.
          </p>
        </div>
      </div>
    );
  }

  const formatDoctorLabel = (doctor: Doctor) => {
    const name = doctor.full_name || 'Unnamed Doctor';
    const specialty = doctor.specialty ? ` • ${doctor.specialty}` : '';
    const department = doctor.department ? ` (${doctor.department})` : '';
    return `${name}${specialty}${department}`;
  };

  const selectedDoctor =
    doctors.find((doctor) => doctor.id === value) || null;

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Assign Doctor *
      </label>
      <select
        value={value || ''}
        onChange={(e) => {
          const doctorId = e.target.value;
          onChange(doctorId);
          if (onSelectDoctor) {
            const selected = doctors.find((doctor) => doctor.id === doctorId);
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
        <option value="">Select a doctor</option>
        {doctors.map((doctor) => (
          <option key={doctor.id} value={doctor.id}>
            {formatDoctorLabel(doctor)}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {selectedDoctor && (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
          <p className="font-semibold text-slate-900">
            {selectedDoctor.full_name || 'Unnamed Doctor'}
          </p>
          {selectedDoctor.specialty && (
            <p>{selectedDoctor.specialty}</p>
          )}
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
            {selectedDoctor.department && (
              <span>Dept: {selectedDoctor.department}</span>
            )}
            {selectedDoctor.room_label && (
              <span>Room: {selectedDoctor.room_label}</span>
            )}
            {selectedDoctor.availability_status && (
              <span>Status: {selectedDoctor.availability_status}</span>
            )}
          </div>
        </div>
      )}
      <p className="text-xs text-gray-500">
        {doctors.length} doctor(s) available
      </p>
    </div>
  );
}
