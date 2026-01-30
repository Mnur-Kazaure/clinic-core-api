// /projects/clinic-monorepo/clinic-app/src/app/reception/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { StartVisitModal } from '@/app/reception/components/visit/StartVisitModal';
import { VisitDetailsModal } from '@/app/reception/components/visit/VisitDetailsModal';
import { VisitQueue } from '@/app/reception/components/visit/VisitQueue';
import { PatientRegistrationForm } from '@/app/reception/components/patient/PatientRegistrationForm';
import { VisitResponse } from '@/shared/types';
import { visitService } from '@/domains/visit/services/visitService';
import { VisitStatusBadge } from '@/ui/VisitStatusBadge';

export default function ReceptionPage() {
  const [isStartVisitModalOpen, setIsStartVisitModalOpen] = useState(false);
  const [showRegistrationForm, setShowRegistrationForm] = useState(false);
  const [refreshQueue, setRefreshQueue] = useState(0);
  const [selectedVisit, setSelectedVisit] = useState<VisitResponse | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [recentVisits, setRecentVisits] = useState<VisitResponse[]>([]);
  const [recentLoading, setRecentLoading] = useState(false);
  const [recentError, setRecentError] = useState<string | null>(null);

  const handleVisitCreated = (visitId: string) => {
    console.log('Visit created:', visitId);
    setIsStartVisitModalOpen(false);
    setRefreshQueue((prev) => prev + 1);
  };

  const handlePatientRegistered = (patientId: string) => {
    console.log('Patient registered:', patientId);
    setShowRegistrationForm(false);
  };

  const handleVisitClick = (visit: VisitResponse) => {
    setSelectedVisit(visit);
    setIsDetailsModalOpen(true);
  };

  const refreshDashboard = () => {
    setRefreshQueue((prev) => prev + 1);
  };

  useEffect(() => {
    let isMounted = true;

    async function loadRecent() {
      try {
        setRecentLoading(true);
        setRecentError(null);
        const data = await visitService.getRecentVisits(5);
        if (isMounted) {
          setRecentVisits(data);
        }
      } catch (error) {
        console.error('Failed to load recent activity:', error);
        if (isMounted) {
          setRecentError('Unable to load recent activity.');
        }
      } finally {
        if (isMounted) {
          setRecentLoading(false);
        }
      }
    }

    loadRecent();
    return () => {
      isMounted = false;
    };
  }, [refreshQueue]);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Reception Dashboard
              </h1>
              <p className="text-gray-600">
                Manage patient visits and clinic workflow
              </p>
            </div>
            <div className="mt-4 sm:mt-0 flex space-x-3">
              <Button
                variant="primary"
                onClick={() => setIsStartVisitModalOpen(true)}
              >
                Start New Visit
              </Button>
              <Button
                variant="secondary"
                onClick={() => setShowRegistrationForm(!showRegistrationForm)}
              >
                {showRegistrationForm
                  ? 'Hide Registration'
                  : 'Register Patient'}
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-600">12</div>
              <p className="text-gray-600">Today's Visits</p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-600">5</div>
              <p className="text-gray-600">Waiting</p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600">7</div>
              <p className="text-gray-600">Completed</p>
            </div>
          </Card>
        </div>

        {showRegistrationForm && (
          <div className="mb-8">
            <PatientRegistrationForm
              onSuccess={handlePatientRegistered}
              onCancel={() => setShowRegistrationForm(false)}
            />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
          <Card title="Quick Actions" titleClassName="text-[#0B4DA2]">
              <div className="space-y-3">
                <Button
                  variant="primary"
                  className="w-full justify-center"
                  onClick={() => setIsStartVisitModalOpen(true)}
                >
                  Start New Visit
                </Button>
                <Button
                  variant="secondary"
                  className="w-full justify-center"
                  onClick={() => setShowRegistrationForm(true)}
                >
                  Register New Patient
                </Button>
                <Button
                  variant="secondary"
                  className="w-full justify-center"
                  onClick={refreshDashboard}
                >
                  Refresh Dashboard
                </Button>
              </div>

              <div className="mt-6 pt-6 border-t">
                <h3 className="text-sm font-medium text-gray-900 mb-3">
                  Recent Activity
                </h3>
                {recentLoading && (
                  <div className="text-sm text-gray-500">Loading activity...</div>
                )}
                {recentError && (
                  <div className="text-sm text-red-600">{recentError}</div>
                )}
                {!recentLoading && !recentError && recentVisits.length === 0 && (
                  <div className="text-sm text-gray-500">
                    No recent visits yet.
                  </div>
                )}
                {!recentLoading && !recentError && recentVisits.length > 0 && (
                  <div className="space-y-3">
                    {recentVisits.map((visit) => (
                      <button
                        key={visit.id}
                        onClick={() => handleVisitClick(visit)}
                        className="w-full rounded-lg border border-gray-200 px-3 py-2 text-left transition hover:bg-gray-50"
                      >
                        <p className="text-sm font-semibold text-gray-900">
                          {visit.patient_name || 'Unknown patient'}
                        </p>
                        <div className="mt-1 flex items-center justify-between text-xs text-gray-600">
                          <VisitStatusBadge status={visit.status} size="sm" />
                          <span>
                            {new Date(visit.updated_at).toLocaleTimeString()}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          </div>

          <div className="lg:col-span-2">
            <VisitQueue
              autoRefresh={true}
              refreshInterval={30000}
              onVisitSelect={(visit) => {
                console.log('Visit selected:', visit.id);
              }}
              onVisitClick={handleVisitClick}
              key={refreshQueue}
            />
          </div>
        </div>

        <StartVisitModal
          isOpen={isStartVisitModalOpen}
          onClose={() => setIsStartVisitModalOpen(false)}
          onSuccess={handleVisitCreated}
        />

        <VisitDetailsModal
          visitId={selectedVisit?.id || null}
          isOpen={isDetailsModalOpen}
          onClose={() => {
            setIsDetailsModalOpen(false);
            setSelectedVisit(null);
          }}
        />
      </main>

      <footer className="bg-white border-t mt-8 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            Clinic Management System • {new Date().toLocaleDateString()}
          </p>
        </div>
      </footer>
    </div>
  );
}
