export const HOSPITAL_NAME = 'Specialist Hospital Kazaure';

const LEGACY_HOSPITAL_NAME_ALIASES = new Set([
  'kazaure specialist hospital',
]);

export function normalizeClinicDisplayName(name?: string | null): string {
  const trimmed = name?.trim();
  if (!trimmed || trimmed.toLowerCase() === 'clinic') {
    return HOSPITAL_NAME;
  }
  if (LEGACY_HOSPITAL_NAME_ALIASES.has(trimmed.toLowerCase())) {
    return HOSPITAL_NAME;
  }
  return trimmed;
}
