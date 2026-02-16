'use client';

import { useEffect, useMemo, useState } from 'react';
import { Card } from '@/shared/Card';
import { Button } from '@/shared/Button';
import {
  ConditionProfile,
  DiagnosisConditionMap,
  DiagnosisMappingConfidence,
  DiagnosisSystem,
  FollowUpPriority,
  followUpService,
  RecallIntervalUnit,
} from '@/domains/followup/services/followupService';

const intervalUnits: RecallIntervalUnit[] = ['DAYS', 'WEEKS', 'MONTHS'];
const priorities: FollowUpPriority[] = ['ROUTINE', 'IMPORTANT', 'CRITICAL'];
const diagnosisSystems: DiagnosisSystem[] = ['ICD10', 'ICPC2', 'LOCAL'];
const mappingConfidences: DiagnosisMappingConfidence[] = ['HIGH', 'MEDIUM'];

export default function FollowUpConfigurationPage() {
  const [profiles, setProfiles] = useState<ConditionProfile[]>([]);
  const [mappings, setMappings] = useState<DiagnosisConditionMap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [profileForm, setProfileForm] = useState({
    code: '',
    display_name: '',
    default_interval_value: '3',
    default_interval_unit: 'MONTHS' as RecallIntervalUnit,
    default_priority: 'IMPORTANT' as FollowUpPriority,
    cooldown_days: '90',
    keyword_synonyms: '',
    recall_enabled: true,
    justification: 'Condition profile setup',
  });

  const [mappingForm, setMappingForm] = useState({
    diagnosis_system: 'ICD10' as DiagnosisSystem,
    diagnosis_code: '',
    condition_profile_id: '',
    confidence: 'HIGH' as DiagnosisMappingConfidence,
    justification: 'Diagnosis mapping setup',
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [profileRows, mappingRows] = await Promise.all([
        followUpService.listConditionProfiles(),
        followUpService.listDiagnosisMappings(),
      ]);
      setProfiles(profileRows);
      setMappings(mappingRows);
      if (!mappingForm.condition_profile_id && profileRows.length > 0) {
        setMappingForm((prev) => ({
          ...prev,
          condition_profile_id: profileRows[0].id,
        }));
      }
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' &&
        err &&
        'response' in err &&
        typeof (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (err as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setError(detail || 'Unable to load follow-up configuration.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const profileLookup = useMemo(() => {
    const index = new Map<string, ConditionProfile>();
    profiles.forEach((profile) => index.set(profile.id, profile));
    return index;
  }, [profiles]);

  const submitProfile = async () => {
    try {
      setError(null);
      setSuccess(null);
      const synonyms = profileForm.keyword_synonyms
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean);
      await followUpService.createConditionProfile({
        code: profileForm.code,
        display_name: profileForm.display_name,
        default_interval_value: Number.parseInt(profileForm.default_interval_value, 10),
        default_interval_unit: profileForm.default_interval_unit,
        default_priority: profileForm.default_priority,
        cooldown_days: Number.parseInt(profileForm.cooldown_days, 10),
        keyword_synonyms: synonyms,
        recall_enabled: profileForm.recall_enabled,
        justification: profileForm.justification,
      });
      setProfileForm((prev) => ({
        ...prev,
        code: '',
        display_name: '',
        keyword_synonyms: '',
      }));
      setSuccess('Condition profile saved.');
      await loadData();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' &&
        err &&
        'response' in err &&
        typeof (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (err as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setError(detail || 'Unable to create condition profile.');
    }
  };

  const toggleProfile = async (profile: ConditionProfile) => {
    try {
      setError(null);
      setSuccess(null);
      await followUpService.updateConditionProfile(profile.id, {
        recall_enabled: !profile.recall_enabled,
        justification: 'Toggle recall enabled state',
      });
      setSuccess('Condition profile updated.');
      await loadData();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' &&
        err &&
        'response' in err &&
        typeof (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (err as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setError(detail || 'Unable to update condition profile.');
    }
  };

  const submitMapping = async () => {
    try {
      setError(null);
      setSuccess(null);
      await followUpService.createDiagnosisMapping({
        diagnosis_system: mappingForm.diagnosis_system,
        diagnosis_code: mappingForm.diagnosis_code,
        condition_profile_id: mappingForm.condition_profile_id,
        confidence: mappingForm.confidence,
        justification: mappingForm.justification,
      });
      setMappingForm((prev) => ({
        ...prev,
        diagnosis_code: '',
      }));
      setSuccess('Diagnosis mapping saved.');
      await loadData();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' &&
        err &&
        'response' in err &&
        typeof (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (err as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setError(detail || 'Unable to create diagnosis mapping.');
    }
  };

  const toggleMapping = async (mapping: DiagnosisConditionMap) => {
    try {
      setError(null);
      setSuccess(null);
      await followUpService.setDiagnosisMappingActive(mapping.id, {
        active: !mapping.active,
        justification: 'Toggle mapping active state',
      });
      setSuccess('Diagnosis mapping updated.');
      await loadData();
    } catch (err: unknown) {
      const detail =
        typeof err === 'object' &&
        err &&
        'response' in err &&
        typeof (err as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail === 'string'
          ? (err as { response?: { data?: { detail?: string } } }).response!.data!
              .detail!
          : null;
      setError(detail || 'Unable to update diagnosis mapping.');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Follow-Up Configuration</h1>
        <p className="mt-1 text-sm text-slate-600">
          Configure chronic condition profiles and diagnosis-code mappings for recall
          suggestions.
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {success}
        </div>
      )}

      <Card title="Condition Profiles">
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            <input
              value={profileForm.code}
              onChange={(event) =>
                setProfileForm((prev) => ({ ...prev, code: event.target.value }))
              }
              className="h-10 rounded-md border border-slate-300 px-3 text-sm"
              placeholder="Code (e.g. HTN)"
            />
            <input
              value={profileForm.display_name}
              onChange={(event) =>
                setProfileForm((prev) => ({ ...prev, display_name: event.target.value }))
              }
              className="h-10 rounded-md border border-slate-300 px-3 text-sm"
              placeholder="Display name"
            />
            <input
              value={profileForm.default_interval_value}
              onChange={(event) =>
                setProfileForm((prev) => ({
                  ...prev,
                  default_interval_value: event.target.value,
                }))
              }
              className="h-10 rounded-md border border-slate-300 px-3 text-sm"
              placeholder="Interval value"
            />
            <select
              value={profileForm.default_interval_unit}
              onChange={(event) =>
                setProfileForm((prev) => ({
                  ...prev,
                  default_interval_unit: event.target.value as RecallIntervalUnit,
                }))
              }
              className="h-10 rounded-md border border-slate-300 px-3 text-sm"
            >
              {intervalUnits.map((unit) => (
                <option key={unit} value={unit}>
                  {unit}
                </option>
              ))}
            </select>
            <select
              value={profileForm.default_priority}
              onChange={(event) =>
                setProfileForm((prev) => ({
                  ...prev,
                  default_priority: event.target.value as FollowUpPriority,
                }))
              }
              className="h-10 rounded-md border border-slate-300 px-3 text-sm"
            >
              {priorities.map((priority) => (
                <option key={priority} value={priority}>
                  {priority}
                </option>
              ))}
            </select>
            <input
              value={profileForm.cooldown_days}
              onChange={(event) =>
                setProfileForm((prev) => ({ ...prev, cooldown_days: event.target.value }))
              }
              className="h-10 rounded-md border border-slate-300 px-3 text-sm"
              placeholder="Cooldown days"
            />
          </div>
          <textarea
            value={profileForm.keyword_synonyms}
            onChange={(event) =>
              setProfileForm((prev) => ({
                ...prev,
                keyword_synonyms: event.target.value,
              }))
            }
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Keyword synonyms (comma-separated)"
          />
          <div className="flex items-center justify-between">
            <label className="inline-flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={profileForm.recall_enabled}
                onChange={(event) =>
                  setProfileForm((prev) => ({
                    ...prev,
                    recall_enabled: event.target.checked,
                  }))
                }
              />
              Recall enabled
            </label>
            <Button
              variant="primary"
              onClick={submitProfile}
              disabled={loading || !profileForm.code || !profileForm.display_name}
            >
              Save Profile
            </Button>
          </div>
        </div>

        <div className="mt-5 overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">Code</th>
                <th className="px-3 py-2">Condition</th>
                <th className="px-3 py-2">Default</th>
                <th className="px-3 py-2">Cooldown</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {profiles.map((profile) => (
                <tr key={profile.id}>
                  <td className="px-3 py-2 font-medium text-slate-900">{profile.code}</td>
                  <td className="px-3 py-2 text-slate-700">{profile.display_name}</td>
                  <td className="px-3 py-2 text-slate-700">
                    {profile.default_interval_value} {profile.default_interval_unit}
                  </td>
                  <td className="px-3 py-2 text-slate-700">{profile.cooldown_days} days</td>
                  <td className="px-3 py-2 text-slate-700">
                    {profile.recall_enabled ? 'Enabled' : 'Disabled'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => toggleProfile(profile)}
                    >
                      {profile.recall_enabled ? 'Disable' : 'Enable'}
                    </Button>
                  </td>
                </tr>
              ))}
              {!loading && profiles.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-slate-500">
                    No condition profiles configured yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title="Diagnosis Mappings">
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <select
            value={mappingForm.diagnosis_system}
            onChange={(event) =>
              setMappingForm((prev) => ({
                ...prev,
                diagnosis_system: event.target.value as DiagnosisSystem,
              }))
            }
            className="h-10 rounded-md border border-slate-300 px-3 text-sm"
          >
            {diagnosisSystems.map((system) => (
              <option key={system} value={system}>
                {system}
              </option>
            ))}
          </select>
          <input
            value={mappingForm.diagnosis_code}
            onChange={(event) =>
              setMappingForm((prev) => ({ ...prev, diagnosis_code: event.target.value }))
            }
            className="h-10 rounded-md border border-slate-300 px-3 text-sm"
            placeholder="Diagnosis code"
          />
          <select
            value={mappingForm.condition_profile_id}
            onChange={(event) =>
              setMappingForm((prev) => ({
                ...prev,
                condition_profile_id: event.target.value,
              }))
            }
            className="h-10 rounded-md border border-slate-300 px-3 text-sm"
          >
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                {profile.display_name}
              </option>
            ))}
          </select>
          <select
            value={mappingForm.confidence}
            onChange={(event) =>
              setMappingForm((prev) => ({
                ...prev,
                confidence: event.target.value as DiagnosisMappingConfidence,
              }))
            }
            className="h-10 rounded-md border border-slate-300 px-3 text-sm"
          >
            {mappingConfidences.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </div>
        <div className="mt-3 flex justify-end">
          <Button
            variant="primary"
            onClick={submitMapping}
            disabled={loading || !mappingForm.diagnosis_code || !mappingForm.condition_profile_id}
          >
            Save Mapping
          </Button>
        </div>

        <div className="mt-5 overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2">System</th>
                <th className="px-3 py-2">Code</th>
                <th className="px-3 py-2">Condition</th>
                <th className="px-3 py-2">Confidence</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {mappings.map((mapping) => (
                <tr key={mapping.id}>
                  <td className="px-3 py-2 text-slate-700">{mapping.diagnosis_system}</td>
                  <td className="px-3 py-2 font-medium text-slate-900">{mapping.diagnosis_code}</td>
                  <td className="px-3 py-2 text-slate-700">
                    {profileLookup.get(mapping.condition_profile_id)?.display_name || 'Unknown'}
                  </td>
                  <td className="px-3 py-2 text-slate-700">{mapping.confidence}</td>
                  <td className="px-3 py-2 text-slate-700">
                    {mapping.active ? 'Active' : 'Inactive'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => toggleMapping(mapping)}
                    >
                      {mapping.active ? 'Disable' : 'Enable'}
                    </Button>
                  </td>
                </tr>
              ))}
              {!loading && mappings.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-4 text-center text-slate-500">
                    No diagnosis mappings configured yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
