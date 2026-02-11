export const jsonUtils = {
  parseVitals(vitals: string | null): Record<string, unknown> | null {
    if (!vitals) return null;
    try {
      return JSON.parse(vitals);
    } catch {
      console.warn('Failed to parse vitals JSON:', vitals);
      return null;
    }
  },

  stringifyVitals(vitals: Record<string, unknown> | null): string | null {
    if (!vitals) return null;
    try {
      return JSON.stringify(vitals);
    } catch {
      console.warn('Failed to stringify vitals:', vitals);
      return null;
    }
  },
};
