'use client';

import { useEffect, useState } from 'react';
import { LabRequestQueue } from '@/app/lab/components/LabRequestQueue';
import { LabRequestDetailsModal } from '@/app/lab/components/LabRequestDetailsModal';
import { roleSessionService } from '@/domains/auth/services/roleSessionService';
import { LabRequest, labService } from '@/domains/lab/services/labService';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

export default function LabPage() {
  const [selectedRequest, setSelectedRequest] = useState<LabRequest | null>(
    null
  );
  const [technicianId, setTechnicianId] = useState<string>('');
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [refreshQueue, setRefreshQueue] = useState(0);
  const [stats, setStats] = useState({
    pending: 0,
    completed: 0,
    cancelled: 0,
  });
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    async function loadTechnician() {
      try {
        const user = await roleSessionService.getCurrentUser();
        setTechnicianId(user.id);
      } catch (error) {
        console.error('Failed to load technician ID:', error);
      }
    }
    loadTechnician();
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadStats() {
      try {
        setStatsLoading(true);
        const data = await labService.getRequests();
        if (!isMounted) return;

        setStats({
          pending: data.filter((r) => r.status === 'PENDING').length,
          completed: data.filter((r) => r.status === 'COMPLETED').length,
          cancelled: data.filter((r) => r.status === 'CANCELLED').length,
        });
      } catch (error) {
        console.error('Failed to load lab stats:', error);
      } finally {
        if (isMounted) {
          setStatsLoading(false);
        }
      }
    }

    loadStats();
    const interval = setInterval(loadStats, 30000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [refreshQueue]);

  const handleRequestClick = (request: LabRequest) => {
    setSelectedRequest(request);
    setIsDetailsModalOpen(true);
  };

  const handleSuccess = () => {
    setRefreshQueue((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Lab Dashboard</h1>
        <p className="text-gray-600">Process lab tests and record results</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">
              {statsLoading ? '—' : stats.pending}
            </div>
            <p className="text-gray-600">Pending Requests</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">
              {statsLoading ? '—' : stats.completed}
            </div>
            <p className="text-gray-600">Completed Requests</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-600">
              {statsLoading ? '—' : stats.cancelled}
            </div>
            <p className="text-gray-600">Cancelled Requests</p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <Card title="Quick Actions" titleClassName="text-[#0B4DA2]">
            <div className="space-y-3">
              <Button
                variant="primary"
                className="w-full justify-center"
                onClick={() => setRefreshQueue((prev) => prev + 1)}
              >
                Refresh Queue
              </Button>
              <Button
                variant="secondary"
                className="w-full justify-center"
                onClick={() => window.open('/api-docs', '_blank')}
              >
                View API Docs
              </Button>
              <Button
                variant="secondary"
                className="w-full justify-center"
                onClick={() => window.location.reload()}
              >
                Reload Dashboard
              </Button>
            </div>

            {technicianId && (
              <div className="mt-6 pt-6 border-t">
                <h3 className="text-sm font-medium text-gray-900 mb-2">
                  Technician Info
                </h3>
                <div className="text-sm text-gray-600">
                  <p>ID: {technicianId.substring(0, 12)}...</p>
                  <p className="mt-1">
                    Results will be recorded under your ID
                  </p>
                </div>
              </div>
            )}

            <div className="mt-6 pt-6 border-t">
              <h3 className="text-sm font-medium text-gray-900 mb-2">
                Recent Activity
              </h3>
              <div className="space-y-3">
                <div className="text-sm">
                  <p className="font-medium">Blood Glucose test completed</p>
                  <p className="text-gray-500">10:30 AM • Result: 5.2 mmol/L</p>
                </div>
                <div className="text-sm">
                  <p className="font-medium">Lipid Profile requested</p>
                  <p className="text-gray-500">10:15 AM • Dr. Smith</p>
                </div>
                <div className="text-sm">
                  <p className="font-medium">Urinalysis in progress</p>
                  <p className="text-gray-500">09:45 AM • Patient: John Doe</p>
                </div>
              </div>
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <LabRequestQueue
            onSelectRequest={handleRequestClick}
            autoRefresh
            refreshInterval={30000}
            key={refreshQueue}
          />
        </div>
      </div>

      {technicianId && (
        <LabRequestDetailsModal
          request={selectedRequest}
          technicianId={technicianId}
          isOpen={isDetailsModalOpen}
          onClose={() => {
            setIsDetailsModalOpen(false);
            setSelectedRequest(null);
          }}
          onSuccess={handleSuccess}
        />
      )}
    </div>
  );
}
