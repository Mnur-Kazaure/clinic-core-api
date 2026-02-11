// /projects/clinic-monorepo/clinic-app/src/domains/patient/schemas/patientSchema.ts
import { z } from 'zod';

export const patientCreateSchema = z.object({
  full_name: z.string().min(2, 'Full name must be at least 2 characters'),
  date_of_birth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be YYYY-MM-DD'),
  gender: z.enum(['MALE', 'FEMALE', 'UNKNOWN']),
  phone_number: z.string().min(10, 'Phone number must be at least 10 digits'),
  address: z.string().min(5, 'Address must be at least 5 characters'),
  occupation: z.string().min(2, 'Occupation must be at least 2 characters'),
  registration_payment_method: z.enum(['CASH', 'TRANSFER']).optional(),
  registration_payment_reference: z.string().optional(),
}).superRefine((data, ctx) => {
  if (data.registration_payment_method === 'TRANSFER') {
    const reference = data.registration_payment_reference?.trim() || '';
    if (reference.length < 3) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Transfer reference is required for bank transfers',
        path: ['registration_payment_reference'],
      });
    }
  }
});

export type PatientCreateFormData = z.infer<typeof patientCreateSchema>;
