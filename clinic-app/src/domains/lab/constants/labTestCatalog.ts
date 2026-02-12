export interface LabTestCatalogEntry {
  name: string;
  category: string;
}

// PHC baseline lab catalog (captured from on-site workflow).
export const PHC_LAB_TEST_CATALOG: LabTestCatalogEntry[] = [
  { name: 'Hemoglobin Estimation (Hb)', category: 'Hematology & Blood' },
  { name: 'Packed Cell Volume (PCV)', category: 'Hematology & Blood' },
  { name: 'Sickling Test', category: 'Hematology & Blood' },
  { name: 'Blood Grouping', category: 'Hematology & Blood' },

  { name: 'Urinalysis', category: 'Urine & Stool' },
  { name: 'Urine Microscopy', category: 'Urine & Stool' },
  { name: 'Stool Microscopy', category: 'Urine & Stool' },

  { name: 'Pregnancy Test (Urine hCG)', category: 'Screening & Metabolic' },
  { name: 'Blood Glucose (Random)', category: 'Screening & Metabolic' },
  { name: 'Blood Glucose (Fasting)', category: 'Screening & Metabolic' },

  { name: 'VDRL', category: 'Infectious Disease' },
  { name: 'Hepatitis B Surface Antigen (HBsAg)', category: 'Infectious Disease' },
  { name: 'Hepatitis C Antibody (HCV)', category: 'Infectious Disease' },
  { name: 'HIV Test', category: 'Infectious Disease' },
  { name: 'Sputum AFB', category: 'Infectious Disease' },
  { name: 'Malaria Parasite Microscopy (MPS)', category: 'Infectious Disease' },
  { name: 'Malaria Rapid Diagnostic Test (mRDT)', category: 'Infectious Disease' },
  { name: 'Widal Test', category: 'Infectious Disease' },
  { name: 'H. pylori Test', category: 'Infectious Disease' },

  {
    name: 'Blood Donor Screening (Weight, Height, BP, Hb/PCV)',
    category: 'Blood Transfusion Services',
  },
  {
    name: 'Donor Blood Screening (HIV, HBsAg, HCV, VDRL)',
    category: 'Blood Transfusion Services',
  },
  { name: 'Blood Bag and Giving Set', category: 'Blood Transfusion Services' },
];
