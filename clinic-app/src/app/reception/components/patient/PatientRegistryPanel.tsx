'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import {
  patientService,
  PatientResponse,
} from '@/domains/patient/services/patientService';
import { PurposeOfUse } from '@/shared/enums';

const PAGE_SIZE = 12;

export function PatientRegistryPanel() {
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(0);
  const [totalPatients, setTotalPatients] = useState(0);
  const [patients, setPatients] = useState<PatientResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedPatient, setSelectedPatient] = useState<PatientResponse | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [detailsError, setDetailsError] = useState<string | null>(null);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(totalPatients / PAGE_SIZE)),
    [totalPatients]
  );

  const loadPatients = async (targetPage: number, term: string) => {
    try {
      setLoading(true);
      setError(null);
      const response = await patientService.listPatients({
        q: term.trim() ? term.trim() : undefined,
        limit: PAGE_SIZE,
        offset: targetPage * PAGE_SIZE,
        purpose_of_use: PurposeOfUse.OPERATIONS,
        justification: 'Reception patient registry review',
      });
      setPatients(response.items);
      setTotalPatients(response.total);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Unable to load patient registry.');
      setPatients([]);
      setTotalPatients(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      void loadPatients(page, searchTerm);
    }, 250);

    return () => clearTimeout(timeoutId);
  }, [page, searchTerm]);

  const openDetails = async (patientId: string) => {
    try {
      setDetailsLoading(true);
      setDetailsError(null);
      setDetailsOpen(true);
      const patient = await patientService.getPatientById(patientId, {
        purpose_of_use: PurposeOfUse.OPERATIONS,
        justification: 'Reception patient detail review',
      });
      setSelectedPatient(patient);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setDetailsError(detail || 'Unable to load patient details.');
      setSelectedPatient(null);
    } finally {
      setDetailsLoading(false);
    }
  };

  const closeDetails = () => {
    setDetailsOpen(false);
    setSelectedPatient(null);
    setDetailsError(null);
  };

  return (
    <Card title="Patient Registry" titleClassName="text-[#0B4DA2]">
      <div className="space-y-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
            <p className="text-xs uppercase tracking-wide text-blue-700">Total Registered Patients</p>
            <p className="mt-2 text-3xl font-semibold text-blue-900">{totalPatients}</p>
            <p className="mt-1 text-xs text-blue-700">Clinic-wide registry count</p>
          </div>
          <div className="md:col-span-2">
            <Input
              label="Search Registry"
              value={searchTerm}
              onChange={(event) => {
                setSearchTerm(event.target.value);
                setPage(0);
              }}
              placeholder="Search by name, phone, address, occupation"
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-600">
            Page {page + 1} of {totalPages}
          </p>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              void loadPatients(page, searchTerm);
            }}
            disabled={loading}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 bg-white">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Patient
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  MRN
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Phone
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Gender
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">
                    Loading patient registry...
                  </td>
                </tr>
              ) : patients.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">
                    No registered patients found.
                  </td>
                </tr>
              ) : (
                patients.map((patient) => (
                  <tr key={patient.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <p className="text-sm font-semibold text-slate-900">{patient.full_name}</p>
                      <p className="text-xs text-slate-500">DOB {patient.date_of_birth}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-700">
                      {patient.patient_mrn || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-700">{patient.phone_number}</td>
                    <td className="px-4 py-3 text-sm text-slate-700">{patient.gender}</td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => {
                          void openDetails(patient.id);
                        }}
                      >
                        View Details
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-end gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={page <= 0 || loading}
            onClick={() => setPage((prev) => Math.max(prev - 1, 0))}
          >
            Previous
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={page + 1 >= totalPages || loading}
            onClick={() => setPage((prev) => prev + 1)}
          >
            Next
          </Button>
        </div>
      </div>

      {detailsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
          <div className="w-full max-w-2xl rounded-xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Patient Details</h3>
                <p className="text-sm text-slate-500">Full registration profile</p>
              </div>
              <button
                type="button"
                onClick={closeDetails}
                className="rounded-md border border-slate-300 px-2 py-1 text-sm text-slate-600 hover:bg-slate-50"
              >
                Close
              </button>
            </div>

            <div className="space-y-3 px-5 py-4">
              {detailsLoading ? (
                <p className="text-sm text-slate-500">Loading details...</p>
              ) : detailsError ? (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {detailsError}
                </div>
              ) : selectedPatient ? (
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Full Name</p>
                    <p className="text-sm font-semibold text-slate-900">{selectedPatient.full_name}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">MRN</p>
                    <p className="text-sm text-slate-900">{selectedPatient.patient_mrn || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Date of Birth</p>
                    <p className="text-sm text-slate-900">{selectedPatient.date_of_birth}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Gender</p>
                    <p className="text-sm text-slate-900">{selectedPatient.gender}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Phone Number</p>
                    <p className="text-sm text-slate-900">{selectedPatient.phone_number}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Occupation</p>
                    <p className="text-sm text-slate-900">{selectedPatient.occupation}</p>
                  </div>
                  <div className="md:col-span-2">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Address</p>
                    <p className="text-sm text-slate-900">{selectedPatient.address}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Identity State</p>
                    <p className="text-sm text-slate-900">{selectedPatient.identity_state || 'VERIFIED'}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Created Reason</p>
                    <p className="text-sm text-slate-900">{selectedPatient.created_reason || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Created At</p>
                    <p className="text-sm text-slate-900">
                      {selectedPatient.created_at
                        ? new Date(selectedPatient.created_at).toLocaleString()
                        : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Updated At</p>
                    <p className="text-sm text-slate-900">
                      {selectedPatient.updated_at
                        ? new Date(selectedPatient.updated_at).toLocaleString()
                        : '—'}
                    </p>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
