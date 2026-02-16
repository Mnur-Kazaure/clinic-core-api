import { ReactNode } from 'react';
import { Badge } from '@/shared/Badge';
import { StatChip } from '@/app/components/common/StatChip';
import { VisitResponse } from '@/shared/types';
import { MaternityDeliveryResponse } from '@/domains/maternity/services/maternityService';

interface MaternityOverviewHeaderProps {
  selectedVisit: VisitResponse | null;
  delivery: MaternityDeliveryResponse | null;
  actionSlot?: ReactNode;
}

export function MaternityOverviewHeader({ selectedVisit, delivery, actionSlot }: MaternityOverviewHeaderProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Maternity overview</p>
          <h2 className="mt-1 text-xl font-semibold text-slate-900">
            {selectedVisit?.patient_name ?? 'Select a patient'}
          </h2>
          <p className="mt-1 text-sm text-slate-600">MRN {selectedVisit?.patient_mrn ?? '—'}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={delivery?.record_status === 'SIGNED' ? 'success' : 'warning'} size="sm">
            {delivery?.record_status ?? 'No signed delivery'}
          </Badge>
          {actionSlot}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
        <StatChip label="Delivery mode" value={delivery?.mode_of_delivery ?? '—'} />
        <StatChip label="Outcome" value={delivery?.outcome ?? '—'} />
        <StatChip label="Baby sex" value={delivery?.baby_sex ?? '—'} />
        <StatChip
          label="Baby weight"
          value={delivery?.baby_weight_kg != null ? `${delivery.baby_weight_kg} kg` : '—'}
          tone="info"
        />
      </div>
    </section>
  );
}
