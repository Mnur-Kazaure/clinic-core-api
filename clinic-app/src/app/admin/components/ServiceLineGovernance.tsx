'use client';

import { Fragment, useEffect, useMemo, useState } from 'react';
import { Alert } from '@/shared/Alert';
import { Button } from '@/shared/Button';
import { Card } from '@/shared/Card';
import { Input } from '@/shared/Input';
import { ServiceLineKind } from '@/shared/enums';
import { clinicService } from '@/domains/clinic/services/clinicService';
import { StaffResponse } from '@/shared/types';
import {
  DepartmentDTO,
  DoctorServiceLineMappingDTO,
  ServiceLineTreeNodeDTO,
  UserDepartmentMappingDTO,
  serviceLineAdminService,
} from '@/domains/admin/services/serviceLineAdminService';

type Banner = {
  variant: 'success' | 'error';
  message: string;
} | null;

type FlattenedServiceLine = {
  node: ServiceLineTreeNodeDTO;
  depth: number;
};

type EditState = {
  id: string;
  name: string;
  parent_id: string;
  department_id: string;
  default_child_id: string;
  requires_doctor: boolean;
  service_line_kind: ServiceLineKind;
  is_active: boolean;
};

const clinicalRoles = new Set(['DOCTOR', 'CHEW', 'MIDWIFE']);

function flattenServiceLines(
  nodes: ServiceLineTreeNodeDTO[],
  depth = 0
): FlattenedServiceLine[] {
  const flattened: FlattenedServiceLine[] = [];
  for (const node of nodes) {
    flattened.push({ node, depth });
    flattened.push(...flattenServiceLines(node.children, depth + 1));
  }
  return flattened;
}

function collectDescendantIds(
  nodeId: string,
  nodesById: Map<string, ServiceLineTreeNodeDTO>
): Set<string> {
  const descendants = new Set<string>();
  const start = nodesById.get(nodeId);
  if (!start) {
    return descendants;
  }

  const stack = [...start.children];
  while (stack.length > 0) {
    const current = stack.pop();
    if (!current || descendants.has(current.id)) {
      continue;
    }
    descendants.add(current.id);
    stack.push(...current.children);
  }
  return descendants;
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (
    typeof error === 'object' &&
    error &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object'
  ) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;
    if (response?.data?.detail && typeof response.data.detail === 'string') {
      return response.data.detail;
    }
  }
  return fallback;
}

export function ServiceLineGovernance() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [banner, setBanner] = useState<Banner>(null);

  const [departments, setDepartments] = useState<DepartmentDTO[]>([]);
  const [serviceLineTree, setServiceLineTree] = useState<ServiceLineTreeNodeDTO[]>([]);
  const [staff, setStaff] = useState<StaffResponse[]>([]);

  const [newName, setNewName] = useState('');
  const [newParentId, setNewParentId] = useState('');
  const [newDepartmentId, setNewDepartmentId] = useState('');
  const [newRequiresDoctor, setNewRequiresDoctor] = useState(true);
  const [newServiceLineKind, setNewServiceLineKind] = useState<ServiceLineKind>(
    ServiceLineKind.GENERAL
  );
  const [creating, setCreating] = useState(false);

  const [editing, setEditing] = useState<EditState | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);
  const [deactivatingId, setDeactivatingId] = useState<string | null>(null);

  const [selectedUserId, setSelectedUserId] = useState('');
  const [userMappings, setUserMappings] = useState<UserDepartmentMappingDTO[]>([]);
  const [userMappingLoading, setUserMappingLoading] = useState(false);
  const [assignDepartmentId, setAssignDepartmentId] = useState('');
  const [assignAsPrimary, setAssignAsPrimary] = useState(false);
  const [assigningUserDepartment, setAssigningUserDepartment] = useState(false);

  const [selectedDoctorId, setSelectedDoctorId] = useState('');
  const [doctorMappings, setDoctorMappings] = useState<DoctorServiceLineMappingDTO[]>([]);
  const [doctorMappingLoading, setDoctorMappingLoading] = useState(false);
  const [assignDoctorServiceLineId, setAssignDoctorServiceLineId] = useState('');
  const [assigningDoctorServiceLine, setAssigningDoctorServiceLine] = useState(false);

  const flattened = useMemo(
    () => flattenServiceLines(serviceLineTree),
    [serviceLineTree]
  );
  const activeLeafLines = useMemo(
    () =>
      flattened
        .map((item) => item.node)
        .filter((node) => node.is_active && node.children.length === 0),
    [flattened]
  );

  const nodesById = useMemo(() => {
    const byId = new Map<string, ServiceLineTreeNodeDTO>();
    for (const item of flattened) {
      byId.set(item.node.id, item.node);
    }
    return byId;
  }, [flattened]);

  const departmentsById = useMemo(() => {
    const byId = new Map<string, DepartmentDTO>();
    for (const department of departments) {
      byId.set(department.id, department);
    }
    return byId;
  }, [departments]);

  const serviceLineById = useMemo(() => {
    const byId = new Map<string, ServiceLineTreeNodeDTO>();
    for (const line of flattened) {
      byId.set(line.node.id, line.node);
    }
    return byId;
  }, [flattened]);

  const clinicalStaff = useMemo(
    () => staff.filter((member) => clinicalRoles.has(member.role)),
    [staff]
  );

  const userCandidates = useMemo(
    () =>
      staff.filter((member) =>
        ['RECEPTION', 'CLINIC_ADMIN', 'DOCTOR', 'CHEW', 'MIDWIFE'].includes(
          member.role
        )
      ),
    [staff]
  );

  const loadCoreData = async (mode: 'initial' | 'refresh' = 'initial') => {
    if (mode === 'initial') {
      setLoading(true);
    } else {
      setRefreshing(true);
    }

    try {
      const [departmentData, serviceLineData, staffData] = await Promise.all([
        serviceLineAdminService.listDepartments(),
        serviceLineAdminService.listServiceLines({ include_inactive: true }),
        clinicService.listStaff(),
      ]);
      setDepartments(departmentData);
      setServiceLineTree(serviceLineData);
      setStaff(staffData);
      setBanner(null);
    } catch (error) {
      setBanner({
        variant: 'error',
        message: extractErrorMessage(
          error,
          'Failed to load service-line governance data.'
        ),
      });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    void loadCoreData('initial');
  }, []);

  useEffect(() => {
    if (!selectedUserId && userCandidates.length > 0) {
      setSelectedUserId(userCandidates[0].id);
    }
  }, [selectedUserId, userCandidates]);

  useEffect(() => {
    if (!selectedDoctorId && clinicalStaff.length > 0) {
      setSelectedDoctorId(clinicalStaff[0].id);
    }
  }, [selectedDoctorId, clinicalStaff]);

  useEffect(() => {
    async function loadUserMappings() {
      if (!selectedUserId) {
        setUserMappings([]);
        return;
      }
      try {
        setUserMappingLoading(true);
        const mappings = await serviceLineAdminService.listUserDepartments(selectedUserId);
        setUserMappings(mappings);
      } catch (error) {
        setBanner({
          variant: 'error',
          message: extractErrorMessage(error, 'Failed to load user-department mappings.'),
        });
      } finally {
        setUserMappingLoading(false);
      }
    }

    void loadUserMappings();
  }, [selectedUserId]);

  useEffect(() => {
    async function loadDoctorMappings() {
      if (!selectedDoctorId) {
        setDoctorMappings([]);
        return;
      }
      try {
        setDoctorMappingLoading(true);
        const mappings = await serviceLineAdminService.listDoctorServiceLines(selectedDoctorId);
        setDoctorMappings(mappings);
      } catch (error) {
        setBanner({
          variant: 'error',
          message: extractErrorMessage(error, 'Failed to load doctor service-line mappings.'),
        });
      } finally {
        setDoctorMappingLoading(false);
      }
    }

    void loadDoctorMappings();
  }, [selectedDoctorId]);

  const handleCreate = async () => {
    const trimmedName = newName.trim();
    if (!trimmedName) {
      setBanner({
        variant: 'error',
        message: 'Service line name is required.',
      });
      return;
    }

    try {
      setCreating(true);
      await serviceLineAdminService.createServiceLine({
        name: trimmedName,
        parent_id: newParentId || null,
        department_id: newParentId ? null : newDepartmentId || null,
        requires_doctor: newRequiresDoctor,
        service_line_kind: newServiceLineKind,
        is_active: true,
      });
      setNewName('');
      setNewParentId('');
      setNewDepartmentId('');
      setNewRequiresDoctor(true);
      setNewServiceLineKind(ServiceLineKind.GENERAL);
      await loadCoreData('refresh');
      setBanner({
        variant: 'success',
        message: 'Service line created successfully.',
      });
    } catch (error) {
      setBanner({
        variant: 'error',
        message: extractErrorMessage(error, 'Failed to create service line.'),
      });
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (line: ServiceLineTreeNodeDTO) => {
    setEditing({
      id: line.id,
      name: line.name,
      parent_id: line.parent_id ?? '',
      department_id: line.department_id ?? '',
      default_child_id: line.default_child_id ?? '',
      requires_doctor: line.requires_doctor,
      service_line_kind: line.service_line_kind,
      is_active: line.is_active,
    });
  };

  const cancelEdit = () => setEditing(null);

  const handleSaveEdit = async () => {
    if (!editing) {
      return;
    }
    const trimmedName = editing.name.trim();
    if (!trimmedName) {
      setBanner({
        variant: 'error',
        message: 'Service line name cannot be blank.',
      });
      return;
    }

    try {
      setSavingEdit(true);
      await serviceLineAdminService.updateServiceLine(editing.id, {
        name: trimmedName,
        parent_id: editing.parent_id || null,
        department_id: editing.parent_id ? null : editing.department_id || null,
        default_child_id: editing.default_child_id || null,
        requires_doctor: editing.requires_doctor,
        service_line_kind: editing.service_line_kind,
        is_active: editing.is_active,
      });
      setEditing(null);
      await loadCoreData('refresh');
      setBanner({
        variant: 'success',
        message: 'Service line updated.',
      });
    } catch (error) {
      setBanner({
        variant: 'error',
        message: extractErrorMessage(error, 'Failed to update service line.'),
      });
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeactivate = async (serviceLineId: string) => {
    if (!confirm('Deactivate this service line? Existing visit history will remain.')) {
      return;
    }
    try {
      setDeactivatingId(serviceLineId);
      await serviceLineAdminService.deactivateServiceLine(serviceLineId);
      await loadCoreData('refresh');
      setBanner({
        variant: 'success',
        message: 'Service line deactivated.',
      });
      if (editing?.id === serviceLineId) {
        setEditing(null);
      }
    } catch (error) {
      setBanner({
        variant: 'error',
        message: extractErrorMessage(error, 'Failed to deactivate service line.'),
      });
    } finally {
      setDeactivatingId(null);
    }
  };

  const handleAssignUserDepartment = async () => {
    if (!selectedUserId || !assignDepartmentId) {
      return;
    }
    try {
      setAssigningUserDepartment(true);
      await serviceLineAdminService.assignUserDepartment(selectedUserId, {
        department_id: assignDepartmentId,
        is_primary: assignAsPrimary,
      });
      const mappings = await serviceLineAdminService.listUserDepartments(selectedUserId);
      setUserMappings(mappings);
      setAssignDepartmentId('');
      setAssignAsPrimary(false);
      setBanner({
        variant: 'success',
        message: 'User-department mapping updated.',
      });
    } catch (error) {
      setBanner({
        variant: 'error',
        message: extractErrorMessage(error, 'Failed to assign department to user.'),
      });
    } finally {
      setAssigningUserDepartment(false);
    }
  };

  const handleRemoveUserDepartment = async (departmentId: string) => {
    if (!selectedUserId) {
      return;
    }
    try {
      await serviceLineAdminService.removeUserDepartment(selectedUserId, departmentId);
      const mappings = await serviceLineAdminService.listUserDepartments(selectedUserId);
      setUserMappings(mappings);
      setBanner({
        variant: 'success',
        message: 'Department mapping removed.',
      });
    } catch (error) {
      setBanner({
        variant: 'error',
        message: extractErrorMessage(error, 'Failed to remove department mapping.'),
      });
    }
  };

  const handleAssignDoctorServiceLine = async () => {
    if (!selectedDoctorId || !assignDoctorServiceLineId) {
      return;
    }
    try {
      setAssigningDoctorServiceLine(true);
      await serviceLineAdminService.assignDoctorServiceLine(selectedDoctorId, {
        service_line_id: assignDoctorServiceLineId,
      });
      const mappings = await serviceLineAdminService.listDoctorServiceLines(selectedDoctorId);
      setDoctorMappings(mappings);
      setAssignDoctorServiceLineId('');
      setBanner({
        variant: 'success',
        message: 'Doctor service-line mapping updated.',
      });
    } catch (error) {
      setBanner({
        variant: 'error',
        message: extractErrorMessage(error, 'Failed to map doctor to service line.'),
      });
    } finally {
      setAssigningDoctorServiceLine(false);
    }
  };

  const handleRemoveDoctorServiceLine = async (serviceLineId: string) => {
    if (!selectedDoctorId) {
      return;
    }
    try {
      await serviceLineAdminService.removeDoctorServiceLine(
        selectedDoctorId,
        serviceLineId
      );
      const mappings = await serviceLineAdminService.listDoctorServiceLines(selectedDoctorId);
      setDoctorMappings(mappings);
      setBanner({
        variant: 'success',
        message: 'Doctor service-line mapping removed.',
      });
    } catch (error) {
      setBanner({
        variant: 'error',
        message: extractErrorMessage(error, 'Failed to remove doctor mapping.'),
      });
    }
  };

  if (loading) {
    return (
      <Card title="Service Line Governance" titleClassName="text-slate-900">
        <div className="space-y-3">
          <div className="h-6 w-1/3 animate-pulse rounded bg-gray-200"></div>
          <div className="h-10 animate-pulse rounded bg-gray-200"></div>
          <div className="h-10 animate-pulse rounded bg-gray-200"></div>
        </div>
      </Card>
    );
  }

  const editingDescendants = editing
    ? collectDescendantIds(editing.id, nodesById)
    : new Set<string>();
  const directChildrenForEditing =
    editing && nodesById.has(editing.id)
      ? nodesById.get(editing.id)?.children ?? []
      : [];

  return (
    <div className="space-y-6">
      {banner && <Alert variant={banner.variant}>{banner.message}</Alert>}

      <Card title="Service Line Catalog" titleClassName="text-slate-900">
        <div className="space-y-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <p className="text-sm text-slate-600">
              Manage service-line hierarchy, default child routing, and doctor requirements.
            </p>
            <Button
              variant="secondary"
              onClick={() => void loadCoreData('refresh')}
              isLoading={refreshing}
              disabled={refreshing}
            >
              Refresh
            </Button>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h4 className="text-sm font-semibold text-slate-900">Add Service Line</h4>
            <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-5">
              <Input
                label="Name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Cardiology"
              />
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Parent
                </label>
                <select
                  value={newParentId}
                  onChange={(e) => setNewParentId(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">None (Root)</option>
                  {flattened.map(({ node, depth }) => (
                    <option key={node.id} value={node.id}>
                      {`${'— '.repeat(depth)}${node.name}`}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Department (Roots)
                </label>
                <select
                  value={newDepartmentId}
                  onChange={(e) => setNewDepartmentId(e.target.value)}
                  disabled={Boolean(newParentId)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                >
                  <option value="">None</option>
                  {departments.map((department) => (
                    <option key={department.id} value={department.id}>
                      {department.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={newRequiresDoctor}
                    onChange={(e) => setNewRequiresDoctor(e.target.checked)}
                    className="h-4 w-4 text-blue-600"
                  />
                  Requires doctor
                </label>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Kind
                </label>
                <select
                  value={newServiceLineKind}
                  onChange={(e) =>
                    setNewServiceLineKind(e.target.value as ServiceLineKind)
                  }
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={ServiceLineKind.GENERAL}>General</option>
                  <option value={ServiceLineKind.LAB_UNIT}>Laboratory Unit</option>
                </select>
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <Button
                variant="primary"
                onClick={() => void handleCreate()}
                isLoading={creating}
                disabled={creating}
              >
                Add Service Line
              </Button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-md border">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Service Line</th>
                  <th className="px-4 py-3 text-left font-medium">Department</th>
                  <th className="px-4 py-3 text-left font-medium">Kind</th>
                  <th className="px-4 py-3 text-left font-medium">Default Child</th>
                  <th className="px-4 py-3 text-left font-medium">Requires Doctor</th>
                  <th className="px-4 py-3 text-left font-medium">Status</th>
                  <th className="px-4 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {flattened.map(({ node, depth }) => {
                  const isEditing = editing?.id === node.id;
                  return (
                    <Fragment key={node.id}>
                      <tr>
                        <td className="px-4 py-3">
                          <div style={{ paddingLeft: `${depth * 16}px` }}>
                            {node.name}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {node.department_id
                            ? departmentsById.get(node.department_id)?.name || 'Unknown'
                            : '—'}
                        </td>
                        <td className="px-4 py-3">
                          {node.service_line_kind === ServiceLineKind.LAB_UNIT
                            ? 'Laboratory Unit'
                            : 'General'}
                        </td>
                        <td className="px-4 py-3">
                          {node.default_child_id
                            ? serviceLineById.get(node.default_child_id)?.name || 'Unknown'
                            : '—'}
                        </td>
                        <td className="px-4 py-3">
                          {node.requires_doctor ? 'Yes' : 'No'}
                        </td>
                        <td className="px-4 py-3">
                          {node.is_active ? 'Active' : 'Inactive'}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="inline-flex gap-2">
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => startEdit(node)}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => void handleDeactivate(node.id)}
                              isLoading={deactivatingId === node.id}
                              disabled={!node.is_active || deactivatingId === node.id}
                            >
                              Deactivate
                            </Button>
                          </div>
                        </td>
                      </tr>
                      {isEditing && editing && (
                        <tr>
                          <td colSpan={7} className="bg-slate-50 px-4 py-4">
                            <div className="grid grid-cols-1 gap-3 lg:grid-cols-7">
                              <Input
                                label="Name"
                                value={editing.name}
                                onChange={(e) =>
                                  setEditing((prev) =>
                                    prev ? { ...prev, name: e.target.value } : prev
                                  )
                                }
                              />
                              <div>
                                <label className="mb-1 block text-sm font-medium text-gray-700">
                                  Parent
                                </label>
                                <select
                                  value={editing.parent_id}
                                  onChange={(e) =>
                                    setEditing((prev) =>
                                      prev
                                        ? {
                                            ...prev,
                                            parent_id: e.target.value,
                                            department_id: e.target.value
                                              ? ''
                                              : prev.department_id,
                                          }
                                        : prev
                                    )
                                  }
                                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                  <option value="">None (Root)</option>
                                  {flattened
                                    .filter(
                                      ({ node: option }) =>
                                        option.id !== editing.id &&
                                        !editingDescendants.has(option.id)
                                    )
                                    .map(({ node: option, depth: optionDepth }) => (
                                      <option key={option.id} value={option.id}>
                                        {`${'— '.repeat(optionDepth)}${option.name}`}
                                      </option>
                                    ))}
                                </select>
                              </div>
                              <div>
                                <label className="mb-1 block text-sm font-medium text-gray-700">
                                  Department (Roots)
                                </label>
                                <select
                                  value={editing.department_id}
                                  onChange={(e) =>
                                    setEditing((prev) =>
                                      prev
                                        ? { ...prev, department_id: e.target.value }
                                        : prev
                                    )
                                  }
                                  disabled={Boolean(editing.parent_id)}
                                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
                                >
                                  <option value="">None</option>
                                  {departments.map((department) => (
                                    <option key={department.id} value={department.id}>
                                      {department.name}
                                    </option>
                                  ))}
                                </select>
                              </div>
                              <div>
                                <label className="mb-1 block text-sm font-medium text-gray-700">
                                  Default Child
                                </label>
                                <select
                                  value={editing.default_child_id}
                                  onChange={(e) =>
                                    setEditing((prev) =>
                                      prev
                                        ? { ...prev, default_child_id: e.target.value }
                                        : prev
                                    )
                                  }
                                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                  <option value="">None</option>
                                  {directChildrenForEditing.map((child) => (
                                    <option key={child.id} value={child.id}>
                                      {child.name}
                                    </option>
                                  ))}
                                </select>
                              </div>
                              <div>
                                <label className="mb-1 block text-sm font-medium text-gray-700">
                                  Kind
                                </label>
                                <select
                                  value={editing.service_line_kind}
                                  onChange={(e) =>
                                    setEditing((prev) =>
                                      prev
                                        ? {
                                            ...prev,
                                            service_line_kind:
                                              e.target.value as ServiceLineKind,
                                          }
                                        : prev
                                    )
                                  }
                                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                  <option value={ServiceLineKind.GENERAL}>General</option>
                                  <option value={ServiceLineKind.LAB_UNIT}>
                                    Laboratory Unit
                                  </option>
                                </select>
                              </div>
                              <div className="flex items-end">
                                <label className="flex items-center gap-2 text-sm text-gray-700">
                                  <input
                                    type="checkbox"
                                    checked={editing.requires_doctor}
                                    onChange={(e) =>
                                      setEditing((prev) =>
                                        prev
                                          ? {
                                              ...prev,
                                              requires_doctor: e.target.checked,
                                            }
                                          : prev
                                      )
                                    }
                                    className="h-4 w-4 text-blue-600"
                                  />
                                  Requires doctor
                                </label>
                              </div>
                              <div className="flex items-end">
                                <label className="flex items-center gap-2 text-sm text-gray-700">
                                  <input
                                    type="checkbox"
                                    checked={editing.is_active}
                                    onChange={(e) =>
                                      setEditing((prev) =>
                                        prev
                                          ? { ...prev, is_active: e.target.checked }
                                          : prev
                                      )
                                    }
                                    className="h-4 w-4 text-blue-600"
                                  />
                                  Active
                                </label>
                              </div>
                            </div>
                            <div className="mt-4 flex justify-end gap-2">
                              <Button variant="secondary" onClick={cancelEdit}>
                                Cancel
                              </Button>
                              <Button
                                variant="primary"
                                onClick={() => void handleSaveEdit()}
                                isLoading={savingEdit}
                                disabled={savingEdit}
                              >
                                Save
                              </Button>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <Card title="User Department Mapping" titleClassName="text-slate-900">
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                User
              </label>
              <select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select user</option>
                {userCandidates.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.full_name || member.email} ({member.role})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Department
              </label>
              <select
                value={assignDepartmentId}
                onChange={(e) => setAssignDepartmentId(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select department</option>
                {departments.map((department) => (
                  <option key={department.id} value={department.id}>
                    {department.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end gap-3">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={assignAsPrimary}
                  onChange={(e) => setAssignAsPrimary(e.target.checked)}
                  className="h-4 w-4 text-blue-600"
                />
                Set as primary
              </label>
              <Button
                onClick={() => void handleAssignUserDepartment()}
                isLoading={assigningUserDepartment}
                disabled={!selectedUserId || !assignDepartmentId || assigningUserDepartment}
              >
                Assign
              </Button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-md border">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Department</th>
                  <th className="px-4 py-3 text-left font-medium">Primary</th>
                  <th className="px-4 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {userMappingLoading && (
                  <tr>
                    <td colSpan={3} className="px-4 py-3 text-gray-500">
                      Loading mappings...
                    </td>
                  </tr>
                )}
                {!userMappingLoading && userMappings.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-3 text-gray-500">
                      No departments mapped for selected user.
                    </td>
                  </tr>
                )}
                {userMappings.map((mapping) => (
                  <tr key={mapping.id}>
                    <td className="px-4 py-3">
                      {departmentsById.get(mapping.department_id)?.name || mapping.department_id}
                    </td>
                    <td className="px-4 py-3">{mapping.is_primary ? 'Yes' : 'No'}</td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => void handleRemoveUserDepartment(mapping.department_id)}
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>

      <Card title="Doctor Service-Line Mapping" titleClassName="text-slate-900">
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Clinical Owner
              </label>
              <select
                value={selectedDoctorId}
                onChange={(e) => setSelectedDoctorId(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select clinical owner</option>
                {clinicalStaff.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.full_name || member.email} ({member.role})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Leaf Service Line
              </label>
              <select
                value={assignDoctorServiceLineId}
                onChange={(e) => setAssignDoctorServiceLineId(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select service line</option>
                {activeLeafLines.map((line) => (
                  <option key={line.id} value={line.id}>
                    {line.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <Button
                onClick={() => void handleAssignDoctorServiceLine()}
                isLoading={assigningDoctorServiceLine}
                disabled={
                  !selectedDoctorId ||
                  !assignDoctorServiceLineId ||
                  assigningDoctorServiceLine
                }
              >
                Assign
              </Button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-md border">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Service Line</th>
                  <th className="px-4 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {doctorMappingLoading && (
                  <tr>
                    <td colSpan={2} className="px-4 py-3 text-gray-500">
                      Loading mappings...
                    </td>
                  </tr>
                )}
                {!doctorMappingLoading && doctorMappings.length === 0 && (
                  <tr>
                    <td colSpan={2} className="px-4 py-3 text-gray-500">
                      No service lines mapped for selected clinical owner.
                    </td>
                  </tr>
                )}
                {doctorMappings.map((mapping) => (
                  <tr key={mapping.id}>
                    <td className="px-4 py-3">
                      {serviceLineById.get(mapping.service_line_id)?.name ||
                        mapping.service_line_id}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() =>
                          void handleRemoveDoctorServiceLine(mapping.service_line_id)
                        }
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Card>
    </div>
  );
}
