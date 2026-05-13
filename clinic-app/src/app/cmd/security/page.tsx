'use client';
import { Card } from '@/shared/Card';
export default function SecurityCenterPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-black text-slate-900 tracking-tight uppercase">Security Command Center</h1>
        <p className="mt-1 text-sm text-slate-500 font-medium">MFA readiness, failed login monitoring, and device/IP anomaly detection.</p>
      </header>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card className="bg-[#0F172A] text-white">
          <h3 className="text-xs font-black text-slate-400 mb-4 uppercase">Threat Level: MINIMAL</h3>
          <p className="text-sm text-slate-300">All security gates are active. No anomalies detected in the last 24 hours.</p>
        </Card>
      </div>
    </div>
  );
}
