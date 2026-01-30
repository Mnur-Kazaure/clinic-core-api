'use client';

import { useEffect, useState } from 'react';
import { PharmacyQueue } from '@/app/pharmacy/components/PharmacyQueue';
import { DispenseForm } from '@/app/pharmacy/components/DispenseForm';
import { PrescriptionDetailsModal } from '@/app/pharmacy/components/PrescriptionDetailsModal';
import { roleSessionService } from '@/domains/auth/services/roleSessionService';
import { pharmacyService } from '@/domains/pharmacy/services/pharmacyService';
import { PrescriptionResponse } from '@/shared/types';
import { PrescriptionStatus } from '@/shared/enums';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';

export default function PharmacyPage() {
  const [selectedPrescription, setSelectedPrescription] =
    useState<PrescriptionResponse | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [pharmacistId, setPharmacistId] = useState<string>('');
  const [isDispenseModalOpen, setIsDispenseModalOpen] = useState(false);
  const [refreshQueue, setRefreshQueue] = useState(0);
  const [stats, setStats] = useState({
    issued: 0,
    dispensed: 0,
    cancelled: 0,
  });
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    async function loadPharmacist() {
      try {
        const user = await roleSessionService.getCurrentUser();
        setPharmacistId(user.id);
      } catch (error) {
        console.error('Failed to load pharmacist ID:', error);
      }
    }
    loadPharmacist();
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadStats() {
      try {
        setStatsLoading(true);
        const data = await pharmacyService.getPrescriptions();
        if (!isMounted) return;
        setStats({
          issued: data.filter((p) => p.status === PrescriptionStatus.ISSUED)
            .length,
          dispensed: data.filter((p) => p.status === PrescriptionStatus.DISPENSED)
            .length,
          cancelled: data.filter((p) => p.status === PrescriptionStatus.CANCELLED)
            .length,
        });
      } catch (error) {
        console.error('Failed to load pharmacy stats:', error);
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

  const handlePrescriptionClick = (prescription: PrescriptionResponse) => {
    setSelectedPrescription(prescription);
    setDetailsOpen(true);
  };

  const handleDispense = (prescription: PrescriptionResponse) => {
    setSelectedPrescription(prescription);
    setIsDispenseModalOpen(true);
  };

  const handleSuccess = () => {
    setRefreshQueue((prev) => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Pharmacy Dashboard
        </h1>
        <p className="text-gray-600">
          Review issued prescriptions and dispense medications
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-600">
              {statsLoading ? '—' : stats.issued}
            </div>
            <p className="text-gray-600">Issued Prescriptions</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-600">
              {statsLoading ? '—' : stats.dispensed}
            </div>
            <p className="text-gray-600">Dispensed Prescriptions</p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-600">
              {statsLoading ? '—' : stats.cancelled}
            </div>
            <p className="text-gray-600">Cancelled Prescriptions</p>
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

            {pharmacistId && (
              <div className="mt-6 pt-6 border-t">
                <h3 className="text-sm font-medium text-gray-900 mb-2">
                  Pharmacist Info
                </h3>
                <div className="text-sm text-gray-600">
                  <p>ID: {pharmacistId.substring(0, 12)}...</p>
                  <p className="mt-1">
                    Dispenses will be recorded under your ID
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>

        <div className="lg:col-span-2">
          <PharmacyQueue
            onSelectPrescription={handlePrescriptionClick}
            onDispensePrescription={handleDispense}
            autoRefresh
            refreshInterval={30000}
            key={refreshQueue}
          />
        </div>
      </div>

      {selectedPrescription && (
        <PrescriptionDetailsModal
          prescription={selectedPrescription}
          isOpen={detailsOpen}
          onClose={() => setDetailsOpen(false)}
          onDispense={handleDispense}
          onRefresh={(updated) => setSelectedPrescription(updated)}
        />
      )}

      {pharmacistId && selectedPrescription && isDispenseModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-900">
                  Dispense Medication
                </h2>
                <button
                  onClick={() => setIsDispenseModalOpen(false)}
                  className="text-gray-400 hover:text-gray-600 text-2xl"
                >
                  ✕
                </button>
              </div>
              <DispenseForm
                prescription={selectedPrescription}
                pharmacistId={pharmacistId}
                onSuccess={() => {
                  handleSuccess();
                  setIsDispenseModalOpen(false);
                  setSelectedPrescription(null);
                  setDetailsOpen(false);
                }}
                onCancel={() => setIsDispenseModalOpen(false)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
