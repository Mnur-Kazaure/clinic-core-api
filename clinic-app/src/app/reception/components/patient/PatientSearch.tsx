'use client';

import { useState, useEffect, useMemo } from 'react';
import debounce from 'lodash/debounce';
import {
  patientService,
  PatientResponse,
} from '@/domains/patient/services/patientService';
import { PurposeOfUse } from '@/shared/enums';

interface PatientSearchProps {
  onSelectPatient: (patient: PatientResponse | null) => void;
  disabled?: boolean;
  purposeOfUse?: PurposeOfUse;
  searchJustification?: string;
}

export function PatientSearch({
  onSelectPatient,
  disabled = false,
  purposeOfUse,
  searchJustification,
}: PatientSearchProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState<PatientResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPatient, setSelectedPatient] =
    useState<PatientResponse | null>(null);

  const performSearch = useMemo(
    () =>
      debounce(async (term: string) => {
        if (!term.trim() || term.trim().length < 2) {
          setResults([]);
          return;
        }

      try {
        const effectivePurpose = purposeOfUse ?? PurposeOfUse.OPERATIONS;
        const effectiveJustification =
          searchJustification?.trim() || 'Reception patient search';

        if (effectiveJustification.length < 2) {
          setError('Search requires an audit justification.');
          setResults([]);
          return;
        }

        setLoading(true);
        setError(null);
        const data = await patientService.searchPatients({
          q: term,
          limit: 10,
          purpose_of_use: effectivePurpose,
          justification: effectiveJustification,
        });
        setResults(data);
      } catch (err: unknown) {
        console.error('Search failed:', err);
        const response =
          typeof err === 'object' && err && 'response' in err
            ? (err as { response?: { status?: number } }).response
            : undefined;
        if (response?.status === 422) {
          setError(
            'Search requires audit justification. Please reload and try again.'
          );
        } else {
          setError('Search failed. Please try again.');
        }
        setResults([]);
      } finally {
        setLoading(false);
      }
      }, 300),
    [purposeOfUse, searchJustification]
  );

  useEffect(() => {
    performSearch(searchTerm);
    return () => {
      performSearch.cancel();
    };
  }, [searchTerm, performSearch]);

  const handleSelect = (patient: PatientResponse) => {
    setSelectedPatient(patient);
    onSelectPatient(patient);
    setSearchTerm(patient.full_name);
    setResults([]);
  };

  const handleClear = () => {
    setSelectedPatient(null);
    setSearchTerm('');
    setResults([]);
    onSelectPatient(null);
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Search Existing Patient
        </label>
        <div className="relative">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            disabled={disabled || selectedPatient !== null}
            placeholder="Search by name or phone number..."
            className={`
              w-full px-3 py-2 border rounded-md shadow-sm
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              ${
                disabled || selectedPatient
                  ? 'bg-gray-100 cursor-not-allowed'
                  : 'border-gray-300'
              }
            `}
          />
          {selectedPatient && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Type at least 2 characters to search
        </p>
      </div>

      {selectedPatient && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-md">
          <div className="flex justify-between items-start">
            <div>
              <p className="font-medium text-green-900">
                {selectedPatient.full_name}
              </p>
              <p className="text-sm text-green-700">
                📞 {selectedPatient.phone_number}
              </p>
              <p className="text-sm text-green-700">
                🎂 {selectedPatient.date_of_birth} • {selectedPatient.gender}
              </p>
            </div>
            <button
              onClick={handleClear}
              className="text-sm text-green-700 hover:text-green-800"
            >
              Change
            </button>
          </div>
        </div>
      )}

      {!selectedPatient && searchTerm.trim().length >= 2 && (
        <div className="border rounded-md shadow-sm max-h-60 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Searching...</p>
            </div>
          ) : error ? (
            <div className="p-4 text-center text-red-600">
              <p>{error}</p>
            </div>
          ) : results.length === 0 ? (
            <div className="p-4 text-center text-gray-500">
              No patients found. Register new patient below.
            </div>
          ) : (
            <ul className="divide-y">
              {results.map((patient) => (
                <li key={patient.id}>
                  <button
                    onClick={() => handleSelect(patient)}
                    className="w-full text-left p-3 hover:bg-gray-50 focus:outline-none focus:bg-gray-50"
                  >
                    <div className="font-medium text-gray-900">
                      {patient.full_name}
                    </div>
                    <div className="text-sm text-gray-700">
                      📞 {patient.phone_number} • 🎂 {patient.date_of_birth}
                    </div>
                    <div className="text-sm text-gray-700">
                      📍{' '}
                      {patient.address
                        ? `${patient.address.substring(0, 30)}${
                            patient.address.length > 30 ? '...' : ''
                          }`
                        : 'Address unavailable'}
                    </div>
                    <div className="mt-2 text-sm font-medium text-blue-600">
                      Use this patient
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
