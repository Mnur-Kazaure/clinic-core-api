'use client';

import { Card } from '@/shared/Card';

const matrix = [
  {
    role: 'Admin',
    permissions: ['Full', 'Full', 'Full', 'Full', 'Full'],
  },
  {
    role: 'Doctor',
    permissions: ['Full', 'Write', 'Write', 'None', 'None'],
  },
  {
    role: 'Reception',
    permissions: ['Create', 'None', 'None', 'View', 'None'],
  },
  {
    role: 'Lab Tech',
    permissions: ['None', 'None', 'Full', 'None', 'None'],
  },
];

const columns = ['Patient', 'Pharmacy', 'Lab', 'Billing', 'Admin'];

export function AccessMatrix() {
  return (
    <Card title="Access Control Matrix" titleClassName="text-slate-900">
      <div className="overflow-x-auto border border-slate-200 rounded-md">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-4 py-3 font-medium">Role</th>
              {columns.map((col) => (
                <th key={col} className="text-left px-4 py-3 font-medium">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {matrix.map((row) => (
              <tr key={row.role}>
                <td className="px-4 py-3 font-medium text-slate-900">
                  {row.role}
                </td>
                {row.permissions.map((perm, idx) => (
                  <td key={idx} className="px-4 py-3 text-slate-600">
                    {perm}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500">
        This matrix is read-only and reflects current guard policies.
      </p>
    </Card>
  );
}
