'use client';

import { useEffect, useMemo, useState } from 'react';
import { clinicService } from '@/domains/clinic/services/clinicService';
import {
  serviceLineAdminService,
  ServiceLineTreeNodeDTO,
} from '@/domains/admin/services/serviceLineAdminService';
import { roleSessionService } from '@/domains/auth/services/roleSessionService';
import { StaffResponse, UserDTO } from '@/shared/types';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import { Input } from '@/shared/Input';
import { Alert } from '@/shared/Alert';
import { StatusBadge } from '@/shared/StatusBadge';
import { ServiceLineKind } from '@/shared/enums';
import { LabUnitOption, StaffFormModal, StaffFormPayload } from './StaffFormModal';

function flattenServiceLines(
  nodes: ServiceLineTreeNodeDTO[],
  lineage: string[] = []
): LabUnitOption[] {
  return nodes.flatMap((node) => {
    const nextLineage = [...lineage, node.name];
    const pathLabel = nextLineage.join(' / ');
    const current: LabUnitOption[] =
      node.service_line_kind === ServiceLineKind.LAB_UNIT &&
      node.children.length === 0 &&
      node.is_active
        ? [
            {
              id: node.id,
              name: node.name,
              path_label: pathLabel,
            },
          ]
        : [];
    return [...current, ...flattenServiceLines(node.children, nextLineage)];
  });
}

export function StaffDirectory() {
  const [staff, setStaff] = useState<StaffResponse[]>([]);
  const [labUnitOptions, setLabUnitOptions] = useState<LabUnitOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<UserDTO | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<'ALL' | StaffResponse['role']>(
    'ALL'
  );
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'DISABLED'>(
    'ALL'
  );
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [selectedStaff, setSelectedStaff] = useState<StaffResponse | null>(null);

  const staffStats = useMemo(() => {
    const total = staff.length;
    const active = staff.filter((member) => member.is_active).length;
    const disabled = staff.filter((member) => !member.is_active).length;
    const cashiers = staff.filter((member) => member.role === 'CASHIER').length;
    const cmdUsers = staff.filter((member) => member.role === 'CMD').length;
    const doctors = staff.filter((member) => member.role === 'DOCTOR').length;
    const labs = staff.filter((member) =>
      ['LAB', 'LAB_TECH', 'LAB_SCIENTIST', 'LAB_SUPERVISOR'].includes(member.role)
    ).length;
    const labManagers = staff.filter((member) => member.role === 'LAB_MANAGER').length;
    const pharmacy = staff.filter((member) => member.role === 'PHARMACY').length;
    const pharmacyHods = staff.filter((member) => member.role === 'PHARMACY_HOD').length;
    const pharmacyStoreOfficers = staff.filter(
      (member) => member.role === 'PHARMACY_STORE_OFFICER'
    ).length;
    return {
      total,
      active,
      disabled,
      cashiers,
      cmdUsers,
      doctors,
      labs,
      labManagers,
      pharmacy,
      pharmacyHods,
      pharmacyStoreOfficers,
    };
  }, [staff]);

  const roleLabel = (role: string) => {
    switch (role) {
      case 'LAB':
        return 'Lab (Legacy)';
      case 'LAB_MANAGER':
        return 'Medical Laboratory HOD';
      case 'CMD':
        return 'Chief Medical Director (CMD)';
      case 'PHARMACY_HOD':
        return 'Pharmacy HOD';
      case 'PHARMACY_STORE_OFFICER':
        return 'Pharmacy Store Officer';
      default:
        return role.replaceAll('_', ' ');
    }
  };

  const filteredStaff = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();
    return staff.filter((member) => {
      const matchesRole = roleFilter === 'ALL' || member.role === roleFilter;
      const matchesStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'ACTIVE' && member.is_active) ||
        (statusFilter === 'DISABLED' && !member.is_active);
      const matchesSearch =
        !term ||
        member.full_name?.toLowerCase().includes(term) ||
        member.email.toLowerCase().includes(term) ||
        member.role.toLowerCase().includes(term);

      return matchesRole && matchesStatus && matchesSearch;
    });
  }, [staff, roleFilter, searchTerm, statusFilter]);

  const loadStaff = async (mode: 'initial' | 'refresh' = 'initial') => {
    try {
      if (mode === 'initial') {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      setError(null);
      const [data, serviceLineTree] = await Promise.all([
        clinicService.listStaff(),
        serviceLineAdminService.listServiceLines(),
      ]);
      setStaff(data);
      setLabUnitOptions(flattenServiceLines(serviceLineTree));
    } catch (err: any) {
      console.error('Failed to load staff list:', err);
      setError('Unable to load staff list.');
    } finally {
      if (mode === 'initial') {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  };

  useEffect(() => {
    loadStaff();
  }, []);

  useEffect(() => {
    async function loadCurrentUser() {
      try {
        const user = await roleSessionService.getCurrentUser();
        setCurrentUser(user);
      } catch (err) {
        console.error('Failed to load current user:', err);
      }
    }

    loadCurrentUser();
  }, []);

  const handleCreate = () => {
    setSelectedStaff(null);
    setModalMode('create');
    setModalOpen(true);
  };

  const handleEdit = (member: StaffResponse) => {
    setSelectedStaff(member);
    setModalMode('edit');
    setModalOpen(true);
  };

  const handleDelete = async (member: StaffResponse) => {
    if (
      !confirm(
        `Delete ${member.full_name || member.email}? This action removes access immediately.`
      )
    ) {
      return;
    }

    try {
      await clinicService.deleteStaff(member.id);
      await loadStaff();
    } catch (err: any) {
      console.error('Failed to delete staff:', err);
      alert(err.response?.data?.detail || 'Failed to delete staff user.');
    }
  };

  const handleSubmit = async (payload: StaffFormPayload) => {
    if (modalMode === 'create') {
      await clinicService.createStaff({
        full_name: payload.full_name,
        email: payload.email,
        password: payload.password || '',
        role: payload.role,
        allowed_lab_unit_ids: payload.allowed_lab_unit_ids || [],
        default_lab_unit_id: payload.default_lab_unit_id || null,
      });
    } else if (selectedStaff) {
      await clinicService.updateStaff(selectedStaff.id, {
        full_name: payload.full_name,
        role: payload.role,
        is_active: payload.is_active,
        specialty: payload.specialty || null,
        department: payload.department || null,
        room_label: payload.room_label || null,
        availability_status: payload.availability_status || null,
        allowed_lab_unit_ids: payload.allowed_lab_unit_ids,
        default_lab_unit_id: payload.default_lab_unit_id || null,
      });
    }

    await loadStaff();
  };

  if (loading) {
    return (
      <Card title="Staff Directory" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="animate-pulse h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
          <div className="animate-pulse h-10 bg-gray-200 rounded"></div>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Staff Directory" titleClassName="text-slate-900">
      <div className="space-y-4">
        {error && <Alert variant="error">{error}</Alert>}

        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex flex-wrap gap-3 text-sm text-gray-600">
            <span>Total: {staffStats.total}</span>
            <span>Active: {staffStats.active}</span>
            <span>Disabled: {staffStats.disabled}</span>
            <span>Cashiers: {staffStats.cashiers}</span>
                <span>Doctors: {staffStats.doctors}</span>
                <span>Lab Managers: {staffStats.labManagers}</span>
                <span>Pharmacy HODs: {staffStats.pharmacyHods}</span>
                <span>Pharmacy Store Officers: {staffStats.pharmacyStoreOfficers}</span>
              </div>
          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={() => loadStaff('refresh')}
              isLoading={refreshing}
            >
              Refresh
            </Button>
            <Button variant="primary" onClick={handleCreate}>
              Add Staff
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Total Staff
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {staffStats.total}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Active
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {staffStats.active}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Disabled
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {staffStats.disabled}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Doctors
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {staffStats.doctors}
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Lab Ops / Lab HOD / Pharmacy
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">
              {staffStats.labs} / {staffStats.labManagers} / {staffStats.pharmacy}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_repeat(2,200px)] gap-3">
          <div>
            <Input
              label="Search staff"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name, email, or role..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Role
            </label>
            <select
              value={roleFilter}
              onChange={(e) =>
                setRoleFilter(e.target.value as typeof roleFilter)
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">All Roles</option>
              <option value="RECEPTION">Reception</option>
              <option value="CASHIER">Cashier</option>
              <option value="ACCOUNTANT">Accountant</option>
              <option value="CMD">Chief Medical Director (CMD)</option>
              <option value="DOCTOR">Doctor</option>
              <option value="LAB">Lab</option>
              <option value="LAB_TECH">Lab Tech</option>
              <option value="LAB_SCIENTIST">Lab Scientist</option>
              <option value="LAB_SUPERVISOR">Lab Supervisor</option>
              <option value="LAB_MANAGER">Lab Manager</option>
              <option value="PHARMACY">Pharmacy</option>
              <option value="PHARMACY_HOD">Pharmacy HOD</option>
              <option value="PHARMACY_STORE_OFFICER">Pharmacy Store Officer</option>
              <option value="CLINIC_ADMIN">Clinic Admin</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as typeof statusFilter)
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="DISABLED">Disabled</option>
            </select>
          </div>
        </div>

        {staff.length === 0 && !error && (
          <div className="rounded-md border border-slate-200 bg-white p-4 text-sm text-gray-600">
            No staff members have been added yet.
          </div>
        )}

        {staff.length > 0 && filteredStaff.length === 0 && !error && (
          <div className="rounded-md border border-slate-200 bg-white p-4 text-sm text-gray-600">
            No staff match the current filters.
          </div>
        )}

        {filteredStaff.length > 0 && (
          <div className="overflow-x-auto border rounded-md">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">Staff</th>
                  <th className="text-left px-4 py-3 font-medium">Role</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-left px-4 py-3 font-medium">Profile</th>
                  <th className="text-right px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredStaff.map((member) => (
                  <tr key={member.id}>
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">
                        {member.full_name || 'Unnamed Staff'}
                      </div>
                      <div className="text-xs text-gray-500">{member.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-gray-800">
                        {roleLabel(member.role)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge
                        label={member.is_active ? 'Active' : 'Disabled'}
                        variant={member.is_active ? 'success' : 'neutral'}
                      />
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600">
                      {member.role === 'DOCTOR' ? (
                        <div className="space-y-1">
                          <div>
                            {member.specialty || 'Specialty not set'}
                          </div>
                          <div>
                            {member.department || 'Department not set'}
                          </div>
                          <div>
                            Room {member.room_label || 'Not assigned'} •{' '}
                            {member.availability_status || 'Status unknown'}
                          </div>
                        </div>
                      ) : ['LAB', 'LAB_TECH', 'LAB_SCIENTIST', 'LAB_SUPERVISOR'].includes(
                          member.role
                        ) ? (
                        <div className="space-y-1">
                          <div>
                            Default unit: {member.default_lab_unit_name || 'Not set'}
                          </div>
                          <div>
                            Units:{' '}
                            {member.allowed_lab_units?.length
                              ? member.allowed_lab_units.map((unit) => unit.name).join(', ')
                              : 'None assigned'}
                          </div>
                        </div>
                      ) : member.role === 'LAB_MANAGER' ? (
                        <span>Lab HOD / oversight workspace</span>
                      ) : member.role === 'PHARMACY_HOD' ? (
                        <span>Pharmacy HOD / governance workspace</span>
                      ) : member.role === 'PHARMACY_STORE_OFFICER' ? (
                        <span>Pharmacy Store / central supply operations</span>
                      ) : (
                        <span>—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleEdit(member)}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => handleDelete(member)}
                        disabled={currentUser?.id === member.id}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <StaffFormModal
        isOpen={modalOpen}
        mode={modalMode}
        initialData={selectedStaff}
        labUnitOptions={labUnitOptions}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSubmit}
      />
    </Card>
  );
}
