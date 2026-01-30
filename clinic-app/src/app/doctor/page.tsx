'use client';

import { useEffect, useMemo, useState } from 'react';
import { ConsultationModal } from '@/app/doctor/components/consultation/ConsultationModal';
import { LabRequestForm } from '@/app/doctor/components/lab/LabRequestForm';
import { PrescriptionForm } from '@/app/doctor/components/prescription/PrescriptionForm';
import { DoctorQueue } from '@/app/doctor/components/DoctorQueue';
import { VisitDetailsModal } from '@/app/reception/components/visit/VisitDetailsModal';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Tooltip } from '@/shared/Tooltip';
import { ConsultationResponse, VisitResponse } from '@/shared/types';
import { consultationService } from '@/domains/consultation/services/consultationService';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';
import { doctorLabService } from '@/domains/lab/services/doctorLabService';
import { LabRequest, LabResult } from '@/domains/lab/services/labService';

export default function DoctorPage() {
  const [selectedVisit, setSelectedVisit] = useState<VisitResponse | null>(null);
  const [consultationVisit, setConsultationVisit] =
    useState<VisitResponse | null>(null);
  const [selectedConsultationId, setSelectedConsultationId] =
    useState<string | null>(null);

  const [isConsultationModalOpen, setIsConsultationModalOpen] = useState(false);
  const [isLabRequestModalOpen, setIsLabRequestModalOpen] = useState(false);
  const [isPrescriptionModalOpen, setIsPrescriptionModalOpen] = useState(false);
  const [isVisitDetailsModalOpen, setIsVisitDetailsModalOpen] = useState(false);
  const [actionWarning, setActionWarning] = useState<string | null>(null);

  const [activeConsultation, setActiveConsultation] = useState<{
    visitId: string;
    consultationId: string;
  } | null>(null);

  const [allVisits, setAllVisits] = useState<VisitResponse[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [activeConsultations, setActiveConsultations] = useState<
    {
      visit: VisitResponse;
      consultation: ConsultationResponse;
      labStatus: 'pending' | 'ready' | 'none';
      labRequestedAt?: string | null;
    }[]
  >([]);

  const [labResultsOpen, setLabResultsOpen] = useState(false);
  const [labResultsLoading, setLabResultsLoading] = useState(false);
  const [labResultsLoadingRequestId, setLabResultsLoadingRequestId] = useState<
    string | null
  >(null);
  const [labResultsError, setLabResultsError] = useState<string | null>(null);
  const [labResultsNotice, setLabResultsNotice] = useState<string | null>(null);
  const [labResults, setLabResults] = useState<LabResult[]>([]);
  const [labRequests, setLabRequests] = useState<LabRequest[]>([]);
  const [selectedLabRequestId, setSelectedLabRequestId] = useState<
    string | null
  >(null);
  const [labRequestInfo, setLabRequestInfo] = useState<LabRequest | null>(null);
  const [doctorFullName, setDoctorFullName] = useState<string | null>(null);
  const [activeConsultationsUpdatedAt, setActiveConsultationsUpdatedAt] =
    useState<Date | null>(null);

  useEffect(() => {
    let isMounted = true;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    async function loadStats() {
      try {
        setStatsLoading(true);
        setStatsError(null);
        const data = await visitService.getDoctorQueue();
        if (isMounted) {
          setAllVisits(data);
        }
      } catch (error) {
        console.error('Failed to load doctor stats:', error);
        if (isMounted) {
          setStatsError('Unable to load live statistics.');
        }
      } finally {
        if (isMounted) {
          setStatsLoading(false);
        }
      }
    }

    loadStats();
    intervalId = setInterval(() => {
      loadStats();
    }, 30000);

    return () => {
      isMounted = false;
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, []);

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const getLabStatusForVisit = async (visitId: string) => {
    try {
      const requests = await doctorLabService.getLabRequestsByVisit(visitId);
      if (requests.length === 0) {
        return { labStatus: 'none' as const, labRequestedAt: null };
      }
      const latest = requests[0];
      const hasCompleted = requests.some((r) => r.status === 'COMPLETED');
      return {
        labStatus: hasCompleted ? 'ready' : 'pending',
        labRequestedAt: latest.created_at,
      };
    } catch {
      return { labStatus: 'none' as const, labRequestedAt: null };
    }
  };

  useEffect(() => {
    let isMounted = true;

    async function loadActiveConsultations() {
      if (allVisits.length === 0) {
        setActiveConsultations([]);
        return;
      }

      const candidates = allVisits.filter((visit) =>
        ['IN_CONSULTATION', 'LAB_REQUESTED', 'LAB_COMPLETED'].includes(
          visit.status
        )
      );

      const entries = await Promise.all(
        candidates.map(async (visit) => {
          try {
            const consultation =
              await consultationService.getConsultationByVisit(visit.id);
            if (!consultation) {
              return null;
            }
            const labState = await getLabStatusForVisit(visit.id);
            return {
              visit,
              consultation,
              labStatus: labState.labStatus,
              labRequestedAt: labState.labRequestedAt,
            };
          } catch {
            return null;
          }
        })
      );

      if (!isMounted) return;
      const active = entries.filter(Boolean) as {
        visit: VisitResponse;
        consultation: ConsultationResponse;
        labStatus: 'pending' | 'ready' | 'none';
        labRequestedAt?: string | null;
      }[];

      setActiveConsultations(active);
      setActiveConsultationsUpdatedAt(new Date());

      if (
        activeConsultation &&
        !active.find((entry) => entry.visit.id === activeConsultation.visitId)
      ) {
        setActiveConsultation(null);
        setConsultationVisit(null);
      }
    }

    loadActiveConsultations();
    return () => {
      isMounted = false;
    };
  }, [allVisits]);

  const stats = useMemo(() => {
    const today = new Date().toDateString();
    const totalToday = allVisits.filter(
      (visit) => new Date(visit.created_at).toDateString() === today
    ).length;
    const inProgress = allVisits.filter(
      (visit) => visit.status === 'IN_CONSULTATION'
    ).length;
    const completedToday = allVisits.filter(
      (visit) =>
        visit.status === 'COMPLETED' &&
        new Date(visit.updated_at).toDateString() === today
    ).length;
    const pendingLab = allVisits.filter(
      (visit) => visit.status === 'LAB_REQUESTED'
    ).length;

    return { totalToday, inProgress, completedToday, pendingLab };
  }, [allVisits]);

  const completedTodayVisits = useMemo(() => {
    const today = new Date().toDateString();
    return allVisits
      .filter(
        (visit) =>
          visit.status === 'COMPLETED' &&
          new Date(visit.updated_at).toDateString() === today
      )
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      .slice(0, 5);
  }, [allVisits]);

  const recentActivity = useMemo(() => {
    return [...allVisits]
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      .slice(0, 3);
  }, [allVisits]);

  const handleStartConsultation = (visit: VisitResponse) => {
    setConsultationVisit(visit);
    setIsConsultationModalOpen(true);
  };

  const handleViewVisit = (visit: VisitResponse) => {
    setSelectedVisit(visit);
    setIsVisitDetailsModalOpen(true);
  };

  const handleConsultationComplete = (consultationId: string) => {
    setSelectedConsultationId(consultationId);
    if (!consultationVisit && selectedVisit) {
      setConsultationVisit(selectedVisit);
    }
    setActiveConsultation({
      visitId: consultationVisit?.id || selectedVisit?.id || '',
      consultationId,
    });
  };

  const handleConsultationReady = async (
    visitId: string,
    consultation: ConsultationResponse
  ) => {
    setActiveConsultation({ visitId, consultationId: consultation.id });
    if (!consultationVisit || consultationVisit.id !== visitId) {
      const visitMatch = allVisits.find((visit) => visit.id === visitId);
      if (visitMatch) {
        setConsultationVisit(visitMatch);
      }
    }
    setDoctorFullName(consultation.doctor_full_name);

    const labState = await getLabStatusForVisit(visitId);
    setActiveConsultations((prev) => {
      const existingIndex = prev.findIndex((entry) => entry.visit.id === visitId);
      const visitMatch =
        prev[existingIndex]?.visit ||
        allVisits.find((visit) => visit.id === visitId) ||
        consultationVisit;

      if (!visitMatch) {
        return prev;
      }

      const entry = {
        visit: visitMatch,
        consultation,
        labStatus: labState.labStatus,
        labRequestedAt: labState.labRequestedAt,
      };

      if (existingIndex === -1) {
        return [entry, ...prev];
      }

      const updated = [...prev];
      updated[existingIndex] = entry;
      return updated;
    });
  };

  const handleResumeConsultation = (visit: VisitResponse) => {
    setConsultationVisit(visit);
    setIsConsultationModalOpen(true);
  };

  const handleSelectConsultationContext = async (visit: VisitResponse) => {
    setConsultationVisit(visit);
    try {
      const consultation = await consultationService.getConsultationByVisit(
        visit.id
      );
      if (consultation) {
        setActiveConsultation({
          visitId: visit.id,
          consultationId: consultation.id,
        });
        setDoctorFullName(consultation.doctor_full_name);
      } else {
        setActiveConsultation(null);
        setDoctorFullName(null);
      }
    } catch {
      setActiveConsultation(null);
      setDoctorFullName(null);
    }
  };

  const loadLabResultsForRequest = async (request: LabRequest) => {
    setLabResultsLoading(true);
    setLabResultsLoadingRequestId(request.id);
    setLabResultsError(null);
    setLabResultsNotice(null);
    setLabResults([]);

    try {
      const results = await doctorLabService.getLabResultsForRequest(request.id);
      setLabResults(results);
      setLabRequestInfo(request);
      setSelectedLabRequestId(request.id);

      if (results.length === 0) {
        const timeAgo = getTimeAgo(request.created_at);
        setLabResultsNotice(`Results pending (sent to lab ${timeAgo}).`);
      }
    } catch (error: any) {
      setLabResultsError(
        error.response?.data?.detail || 'Unable to load lab results.'
      );
    } finally {
      setLabResultsLoading(false);
      setLabResultsLoadingRequestId(null);
    }
  };

  const handleCheckLabResults = async () => {
    if (!activeConsultation) return;
    setLabResultsOpen(true);
    setLabResultsError(null);
    setLabResultsNotice(null);
    setLabResults([]);
    setLabRequests([]);
    setSelectedLabRequestId(null);
    setLabRequestInfo(null);

    try {
      setLabResultsLoading(true);
      try {
        const consultation = await consultationService.getConsultationByVisit(
          activeConsultation.visitId
        );
        if (consultation) {
          setDoctorFullName(consultation.doctor_full_name);
        }
      } catch {
        setDoctorFullName(null);
      }

      const requests = await doctorLabService.getLabRequestsByVisit(
        activeConsultation.visitId
      );
      const sortedRequests = [...requests].sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setLabRequests(sortedRequests);

      if (sortedRequests.length === 0) {
        setLabResultsNotice('No lab order found for this visit.');
        setLabResultsLoading(false);
        return;
      }

      const latestRequest = sortedRequests[0];
      await loadLabResultsForRequest(latestRequest);
    } catch (error: any) {
      setLabResultsError(
        error.response?.data?.detail || 'Unable to load lab results.'
      );
      setLabResultsLoading(false);
    }
  };

  const handleRequestLab = () => {
    if (!activeConsultation) return;
    setIsLabRequestModalOpen(true);
  };

  const handleIssuePrescription = () => {
    if (!activeConsultation) return;
    setIsPrescriptionModalOpen(true);
  };

  const handleRestrictedAction = (action: 'lab' | 'prescription') => {
    const message =
      action === 'lab'
        ? 'A consultation must be started before ordering lab tests.'
        : 'A consultation must be started before issuing prescriptions.';
    setActionWarning(message);
  };

  const handleLabRequestSuccess = (labRequestId: string) => {
    console.log('Lab request created:', labRequestId);
    setIsLabRequestModalOpen(false);
  };

  const handlePrescriptionSuccess = (prescriptionId: string) => {
    console.log('Prescription issued:', prescriptionId);
    setIsPrescriptionModalOpen(false);
  };

  const getQuickActions = () => {
    if (
      !activeConsultation ||
      !consultationVisit ||
      activeConsultation.visitId !== consultationVisit.id
    ) {
      return null;
    }

    const activeEntry = activeConsultations.find(
      (entry) => entry.visit.id === activeConsultation.visitId
    );
    const isConsultationCompleted = Boolean(
      activeEntry?.consultation.completed_at
    );
    const labStatus = activeEntry?.labStatus ?? 'none';

    return (
      <Card title="Consultation Actions" titleClassName="!text-[#0B4DA2]">
        <div className="space-y-4">
          <div className="text-sm text-gray-700">
            Patient:{' '}
            <span className="font-medium text-gray-900">
              {consultationVisit.patient_name || 'Unknown patient'}
            </span>
            <span className="text-gray-500">
              {' '}
              • Visit {consultationVisit.id.substring(0, 8)}...
            </span>
          </div>
          {isConsultationCompleted ? (
            <div className="flex items-center gap-2 text-sm text-gray-700">
              <Tooltip
                content="Record is locked and read-only."
                widthClassName="w-64"
              >
                <span className="inline-flex items-center rounded-full bg-[#E6F4FB] px-2 py-0.5 text-xs font-medium text-[#0B4DA2]">
                  Consultation completed
                </span>
              </Tooltip>
            </div>
          ) : (
            <p className="text-sm text-gray-600">
              Continue documentation or proceed to labs and prescriptions.
            </p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Button
              variant={isConsultationCompleted ? 'secondary' : 'primary'}
              onClick={() => setIsConsultationModalOpen(true)}
              className="w-full justify-center"
            >
              {isConsultationCompleted
                ? 'View Completed Consultation'
                : 'Continue Consultation'}
            </Button>

            {isConsultationCompleted ? (
              <Tooltip content="Consultation is completed and locked.">
                <div>
                  <Button
                    variant="secondary"
                    onClick={handleRequestLab}
                    className="w-full justify-center"
                    disabled
                  >
                    Request Lab Test
                  </Button>
                </div>
              </Tooltip>
            ) : (
              <Button
                variant="secondary"
                onClick={handleRequestLab}
                className="w-full justify-center"
              >
                Request Lab Test
              </Button>
            )}

            {isConsultationCompleted ? (
              <Tooltip content="Consultation is completed and locked.">
                <div>
                  <Button
                    variant="secondary"
                    onClick={handleIssuePrescription}
                    className="w-full justify-center"
                    disabled
                  >
                    Issue Prescription
                  </Button>
                </div>
              </Tooltip>
            ) : (
              <Button
                variant="secondary"
                onClick={handleIssuePrescription}
                className="w-full justify-center"
              >
                Issue Prescription
              </Button>
            )}

            <Button
              variant="secondary"
              onClick={() => setIsVisitDetailsModalOpen(true)}
              className="w-full justify-center"
            >
              View Visit Details
            </Button>

            <Button
              variant="secondary"
              onClick={handleCheckLabResults}
              className="w-full justify-center"
            >
              <span className="flex w-full items-center justify-between gap-3">
                <span className="inline-flex items-center gap-2 text-left">
                  <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    className="h-4 w-4 text-slate-600"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M10 2h4" />
                    <path d="M12 2v6l4.5 7.8a3 3 0 0 1-2.6 4.5H10.1a3 3 0 0 1-2.6-4.5L12 8" />
                    <path d="M8.5 14h7" />
                  </svg>
                  <span className="whitespace-nowrap">Lab Results</span>
                </span>
                {labStatus !== 'none' ? (
                  <span
                    className={`inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${
                      labStatus === 'ready'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {labStatus === 'ready' ? 'Results ready' : 'Pending'}
                  </span>
                ) : (
                  <span className="inline-flex items-center whitespace-nowrap rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
                    No lab order
                  </span>
                )}
              </span>
            </Button>
          </div>
        </div>
      </Card>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-semibold text-[#0B4DA2]">
                Doctor Dashboard
              </h1>
              <p className="text-sm text-gray-600">
                Clinical workspace for consultations, prescriptions, and lab requests.
              </p>
            </div>

            {activeConsultation && (
              <div className="mt-4 sm:mt-0">
                <div className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-[#E6F4FB] text-[#0B4DA2]">
                  Active Consultation
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Overview</h2>
          <p className="text-sm text-gray-600">
            At-a-glance status of today&apos;s workload and active cases.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-10">
          <Card>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Today's Consultations
              </p>
              <div className="mt-2 text-3xl font-semibold text-[#0B4DA2]">
                {statsLoading ? '—' : stats.totalToday}
              </div>
              {statsError && (
                <p className="text-xs text-red-600 mt-2">{statsError}</p>
              )}
            </div>
          </Card>
          <Card>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">
                In Progress
              </p>
              <div className="mt-2 text-3xl font-semibold text-[#1E88E5]">
                {statsLoading ? '—' : stats.inProgress}
              </div>
            </div>
          </Card>
          <Card>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Completed Today
              </p>
              <div className="mt-2 text-3xl font-semibold text-[#18B2A7]">
                {statsLoading ? '—' : stats.completedToday}
              </div>
            </div>
          </Card>
          <Card>
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Pending Lab Results
              </p>
              <div className="mt-2 text-3xl font-semibold text-[#4A5A66]">
                {statsLoading ? '—' : stats.pendingLab}
              </div>
            </div>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Patient Queue</h2>
              <p className="text-sm text-gray-600">
                Assigned visits that require your attention.
              </p>
            </div>
            <DoctorQueue
              onStartConsultation={handleStartConsultation}
              onViewVisit={handleViewVisit}
              onSelectPatient={(visit, hasConsultation) => {
                if (hasConsultation) {
                  handleSelectConsultationContext(visit);
                }
              }}
            />
          </div>

          <div className="space-y-6">
            <Card title="Active Consultations" titleClassName="!text-[#0B4DA2]">
              <div className="mb-3 text-xs text-gray-500">
                Last updated:{' '}
                {activeConsultationsUpdatedAt
                  ? activeConsultationsUpdatedAt.toLocaleTimeString()
                  : '—'}
              </div>
              {activeConsultations.length === 0 && (
                <p className="text-sm text-gray-500">
                  No active consultations yet.
                </p>
              )}
              {activeConsultations.length > 0 && (
                <div className="space-y-3">
                  {activeConsultations.map((entry) => (
                    <div
                      key={entry.visit.id}
                      className={`rounded-md border p-3 ${
                        consultationVisit?.id === entry.visit.id
                          ? 'border-blue-200 bg-blue-50'
                          : 'border-gray-200 bg-white'
                      }`}
                      onClick={() => handleSelectConsultationContext(entry.visit)}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">
                            {entry.visit.patient_name || 'Unknown patient'}
                          </p>
                          <p className="text-xs text-gray-500">
                            Visit {entry.visit.id.substring(0, 8)}... •{' '}
                            {getTimeAgo(entry.consultation.started_at)} in consult
                          </p>
                          {entry.consultation.completed_at && (
                            <span className="mt-2 inline-flex items-center rounded-full bg-[#E6F4FB] px-2 py-0.5 text-xs font-medium text-[#0B4DA2]">
                              Consultation completed
                            </span>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          {entry.labStatus !== 'none' && (
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                entry.labStatus === 'ready'
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}
                            >
                              {entry.labStatus === 'ready'
                                ? 'Results ready'
                                : 'Lab pending'}
                            </span>
                          )}
                          {entry.labStatus === 'pending' &&
                            entry.labRequestedAt && (
                              <span className="text-xs text-gray-500">
                                Sent {getTimeAgo(entry.labRequestedAt)}
                              </span>
                            )}
                          {!entry.consultation.completed_at && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleResumeConsultation(entry.visit);
                              }}
                              className="text-xs font-medium text-blue-700 hover:text-blue-800 underline underline-offset-2"
                            >
                              Resume
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {getQuickActions() || (
              <Card title="Quick Actions">
                <div className="space-y-3">
                  <p className="text-sm text-gray-600 mb-4">
                    Select a patient from the queue to begin consultation.
                  </p>

                  <div className="space-y-2">
                    <div className="flex items-center text-sm text-gray-600">
                      <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                      <span>Click "Start Consultation" on a patient</span>
                    </div>
                    <div className="flex items-center text-sm text-gray-600">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                      <span>Record vitals and medical notes</span>
                    </div>
                    <div className="flex items-center text-sm text-gray-600">
                      <div className="w-2 h-2 bg-purple-500 rounded-full mr-2"></div>
                      <span>Request labs or prescribe medication</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                    <Button
                      variant="secondary"
                      onClick={() => handleRestrictedAction('lab')}
                      className="w-full justify-center"
                    >
                      Request Lab Test
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => handleRestrictedAction('prescription')}
                      className="w-full justify-center"
                    >
                      Issue Prescription
                    </Button>
                  </div>

                  {actionWarning && (
                    <div className="rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
                      {actionWarning}
                      <button
                        type="button"
                        onClick={() => setActionWarning(null)}
                        className="ml-3 text-yellow-900 underline underline-offset-2"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {activeConsultation && (
              <Card>
                <div className="text-sm text-gray-700">
                  Resume consultation to finalize notes or place orders.
                </div>
              </Card>
            )}

            <Card
              title="Completed Visits Today"
              titleClassName="!text-[#0B4DA2]"
            >
              {completedTodayVisits.length === 0 && (
                <p className="text-sm text-gray-500">
                  No completed visits today yet.
                </p>
              )}
              {completedTodayVisits.length > 0 && (
                <div className="space-y-3">
                  {completedTodayVisits.map((visit) => (
                    <div
                      key={visit.id}
                      className="rounded-md border border-gray-100 bg-gray-50 p-3 text-sm"
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-gray-900">
                          {visit.patient_name || 'Unknown patient'}
                        </p>
                        <span className="text-xs text-gray-500">
                          {new Date(visit.updated_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="mt-2">
                        <VisitStatusBadge status={visit.status} size="sm" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card title="Recent Activity" titleClassName="!text-[#0B4DA2]">
              {recentActivity.length === 0 && (
                <p className="text-sm text-gray-500">
                  No recent updates yet.
                </p>
              )}
              {recentActivity.length > 0 && (
                <div className="space-y-3">
                  {recentActivity.map((visit) => (
                    <div
                      key={visit.id}
                      className="rounded-md border border-gray-100 bg-gray-50 p-3 text-sm"
                    >
                      <div className="flex items-center justify-between">
                        <p className="font-medium text-gray-900">
                          {visit.patient_name || 'Unknown patient'}
                        </p>
                        <span className="text-xs text-gray-500">
                          {new Date(visit.updated_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="mt-2">
                        <VisitStatusBadge status={visit.status} size="sm" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      </main>

      {consultationVisit && (
        <ConsultationModal
          visitId={consultationVisit.id}
          visitSummary={{
            patientName: consultationVisit.patient_name,
            status: consultationVisit.status,
          }}
          isOpen={isConsultationModalOpen}
          onClose={() => {
            setIsConsultationModalOpen(false);
            if (
              !activeConsultation ||
              activeConsultation.visitId !== consultationVisit.id
            ) {
              setConsultationVisit(null);
            }
          }}
          onComplete={handleConsultationComplete}
          onConsultationReady={handleConsultationReady}
          existingConsultation={null}
        />
      )}

      {labResultsOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-slate-200">
            <div className="border-b border-slate-200 bg-[#F5FAFE] px-6 py-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[#0B4DA2]">
                    Lab Results
                  </p>
                  <h2 className="text-2xl font-semibold text-slate-900 mt-1">
                    Diagnostic Results Review
                  </h2>
                  {consultationVisit && (
                    <p className="text-sm text-slate-600 mt-1">
                      {consultationVisit.patient_name || 'Unknown patient'} •
                      Visit {consultationVisit.id.substring(0, 12)}...
                    </p>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {consultationVisit && (
                      <span className="inline-flex items-center rounded-full bg-[#E6F4FB] px-2.5 py-0.5 text-xs font-medium text-[#0B4DA2]">
                        Status: {consultationVisit.status}
                      </span>
                    )}
                    {labRequestInfo && (
                      <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                        Test: {labRequestInfo.test_name}
                      </span>
                    )}
                    {consultationVisit &&
                      consultationVisit.assigned_doctor_id && (
                        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                          Attending doctor: {doctorFullName || '—'}
                        </span>
                      )}
                  </div>
                  {labRequestInfo && (
                    <p className="text-xs text-slate-500 mt-2">
                      Source: Lab request {labRequestInfo.id.substring(0, 8)}... •
                      Status {labRequestInfo.status}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => setLabResultsOpen(false)}
                  className="text-slate-400 hover:text-slate-600 text-2xl leading-none"
                  aria-label="Close lab results"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="px-6 py-5 space-y-4">
              {labRequests.length > 0 && (
                <div className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Lab Requests
                    </p>
                    <span className="text-xs text-slate-500">
                      {labRequests.length} total
                    </span>
                  </div>
                  <div className="mt-3 space-y-2">
                    {labRequests.map((request, index) => {
                      const isSelected = request.id === selectedLabRequestId;
                      const isLoading = request.id === labResultsLoadingRequestId;
                      return (
                        <button
                          key={request.id}
                          type="button"
                          onClick={() => loadLabResultsForRequest(request)}
                          className={`w-full rounded-md border px-3 py-2 text-left transition ${
                            isSelected
                              ? 'border-blue-200 bg-blue-50 border-l-4 border-l-[#0B4DA2] shadow-sm'
                              : 'border-slate-200 hover:border-blue-200 hover:bg-blue-50/50'
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-sm font-medium text-slate-900">
                              {request.test_name}
                            </span>
                            <div className="flex items-center gap-2">
                              {isLoading && (
                                <span className="inline-flex items-center gap-1 rounded-full bg-[#E6F4FB] px-2 py-0.5 text-xs font-medium text-[#0B4DA2]">
                                  <svg
                                    className="h-3 w-3 animate-spin text-[#0B4DA2]"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                  >
                                    <circle
                                      className="opacity-25"
                                      cx="12"
                                      cy="12"
                                      r="9"
                                    />
                                    <path
                                      className="opacity-75"
                                      d="M12 3a9 9 0 0 1 9 9"
                                    />
                                  </svg>
                                  <span>Loading</span>
                                </span>
                              )}
                              {isSelected && (
                                <span className="inline-flex items-center rounded-full bg-[#E6F4FB] px-2 py-0.5 text-xs font-medium text-[#0B4DA2]">
                                  Selected
                                </span>
                              )}
                              {index === 0 && (
                                <span className="inline-flex items-center rounded-full bg-[#E6F4FB] px-2 py-0.5 text-xs font-medium text-[#0B4DA2]">
                                  Latest
                                </span>
                              )}
                              <span
                                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                  request.status === 'COMPLETED'
                                    ? 'bg-green-100 text-green-800'
                                    : request.status === 'CANCELLED'
                                      ? 'bg-slate-100 text-slate-600'
                                      : 'bg-yellow-100 text-yellow-800'
                                }`}
                              >
                                {request.status}
                              </span>
                            </div>
                          </div>
                          <p className="mt-1 text-xs text-slate-500">
                            Requested {getTimeAgo(request.created_at)}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
              {labResultsLoading && (
                <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
                  Loading results...
                </div>
              )}
              {!labResultsLoading && labResultsError && (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                  {labResultsError}
                </div>
              )}
              {!labResultsLoading && !labResultsError && labResultsNotice && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  {labResultsNotice}
                </div>
              )}

              {!labResultsLoading &&
                !labResultsError &&
                labResults.length > 0 && (
                  <div className="space-y-3">
                    {labResults.map((result) => (
                      <div
                        key={result.id}
                        className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-base font-semibold text-slate-900">
                            {result.result_value} {result.result_unit}
                          </span>
                          <span className="text-xs text-slate-500">
                            {new Date(result.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="mt-2 text-sm text-slate-600">
                          Reference range: {result.reference_range}
                        </div>
                        <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
                          <span>
                            Technician: {result.technician_id.substring(0, 12)}...
                          </span>
                          <span>Result ID: {result.id.substring(0, 8)}...</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

              <div className="flex justify-end pt-2">
                <Button
                  variant="secondary"
                  onClick={() => setLabResultsOpen(false)}
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeConsultation && isLabRequestModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  Request Lab Test
                </h2>
                <button
                  onClick={() => setIsLabRequestModalOpen(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ✕
                </button>
              </div>

              <LabRequestForm
                visitId={activeConsultation.visitId}
                consultationId={activeConsultation.consultationId}
                onSuccess={handleLabRequestSuccess}
                onCancel={() => setIsLabRequestModalOpen(false)}
                compact
              />
            </div>
          </div>
        </div>
      )}

      {activeConsultation && isPrescriptionModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  Issue Prescription
                </h2>
                <button
                  onClick={() => setIsPrescriptionModalOpen(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ✕
                </button>
              </div>

              <PrescriptionForm
                visitId={activeConsultation.visitId}
                consultationId={activeConsultation.consultationId}
                onSuccess={handlePrescriptionSuccess}
                onCancel={() => setIsPrescriptionModalOpen(false)}
                compact
              />
            </div>
          </div>
        </div>
      )}

      {selectedVisit && (
        <VisitDetailsModal
          visitId={selectedVisit.id}
          isOpen={isVisitDetailsModalOpen}
          onClose={() => {
            setIsVisitDetailsModalOpen(false);
            setSelectedVisit(null);
          }}
          hiddenTransitions={['LAB_REQUESTED']}
        />
      )}

      <footer className="bg-white border-t mt-8 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            Doctor Portal • Clinic Management System •{' '}
            {new Date().toLocaleDateString()}
          </p>
        </div>
      </footer>
    </div>
  );
}
