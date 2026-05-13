'use client';
import { useEffect, useState } from 'react';
import client from '@/api/client';

interface Visit {
  id: string;
  started_at: string;
  service_line: string;
  status: string;
}

interface PatientProfile {
  id: string;
  full_name: string;
  date_of_birth: string;
  gender: string;
  phone_number: string;
  address: string;
  total_visits: number;
  active_admission: boolean;
  latest_visits: Visit[];
}

export function PatientModal({ patientId, onClose }: { patientId: string; onClose: () => void }) {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProfile() {
      try {
        const res = await client.get(`/v1/cmd/patient/${patientId}`);
        setProfile(res.data);
      } catch (err) {
        console.error('Failed to fetch patient profile', err);
      } finally {
        setLoading(false);
      }
    }
    fetchProfile();
  }, [patientId]);

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden border border-slate-200">
        <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <div>
            <h2 className="text-xl font-black text-slate-900 tracking-tight uppercase">Patient Clinical Profile</h2>
            <p className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest mt-0.5">Executive Record Access</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-lg transition-colors">
            <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-8">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 space-y-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Retrieving Health Records...</p>
            </div>
          ) : profile ? (
            <div className="space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-6">
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Full Name</label>
                    <p className="text-lg font-black text-slate-900">{profile.full_name}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">D.O.B</label>
                      <p className="font-bold text-slate-700">{profile.date_of_birth}</p>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Gender</label>
                      <p className="font-bold text-slate-700">{profile.gender}</p>
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Contact</label>
                    <p className="font-bold text-slate-700">{profile.phone_number || 'N/A'}</p>
                  </div>
                </div>

                <div className="bg-slate-50 rounded-xl p-6 border border-slate-100 flex flex-col justify-center text-center space-y-4">
                   <div>
                      <p className="text-4xl font-black text-indigo-900 leading-none">{profile.total_visits}</p>
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-2">Total Institutional Visits</p>
                   </div>
                   {profile.active_admission && (
                     <div className="bg-rose-50 border border-rose-100 px-3 py-1.5 rounded-lg">
                        <p className="text-[10px] font-black text-rose-600 uppercase tracking-tighter">CURRENTLY ADMITTED</p>
                     </div>
                   )}
                </div>
              </div>

              <div>
                <h3 className="text-xs font-black text-slate-900 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <div className="w-1 h-4 bg-indigo-600 rounded-full"></div>
                  Recent Clinical Activity
                </h3>
                <div className="space-y-2">
                  {profile.latest_visits.length > 0 ? (
                    profile.latest_visits.map((v) => (
                      <div key={v.id} className="flex items-center justify-between p-3 bg-white border border-slate-100 rounded-lg hover:border-indigo-200 transition-colors">
                        <div className="flex items-center gap-3">
                          <div className={`w-2 h-2 rounded-full ${v.status === 'COMPLETED' ? 'bg-emerald-500' : 'bg-indigo-500'}`}></div>
                          <div>
                            <p className="text-xs font-bold text-slate-900">{v.service_line}</p>
                            <p className="text-[10px] text-slate-500 font-medium">{new Date(v.started_at).toLocaleDateString()} • {new Date(v.started_at).toLocaleTimeString()}</p>
                          </div>
                        </div>
                        <span className={`text-[9px] font-black px-2 py-1 rounded-md tracking-tighter ${v.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-600' : 'bg-indigo-50 text-indigo-600'}`}>
                          {v.status}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="text-center py-6 text-xs text-slate-400 font-medium italic">No recent visit history found.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-slate-500 font-medium">Patient record could not be retrieved.</p>
            </div>
          )}
        </div>

        <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-end">
          <button onClick={onClose} className="px-6 py-2 bg-slate-900 text-white rounded-lg text-xs font-bold uppercase tracking-widest hover:bg-slate-800 transition-all shadow-lg shadow-slate-200">
            Close Record
          </button>
        </div>
      </div>
    </div>
  );
}
