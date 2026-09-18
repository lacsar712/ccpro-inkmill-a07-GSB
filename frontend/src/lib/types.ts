export type UserRole = 'admin' | 'grinder';

export interface AuthUser {
  id: number;
  username: string;
  displayName: string;
  role: UserRole | string;
}

export interface Workshop {
  id: number;
  name: string;
  site: string | null;
  notes: string | null;
}

export type MillStatus = 'grinding' | 'idle' | 'wash';

export interface Mill {
  id: number;
  workshopId: number;
  millCode: string;
  pigmentBase: string;
  bowlLiters: number;
  status: MillStatus;
}

export interface ViscositySample {
  id: number;
  millId: number;
  sampledAt: string;
  viscosityPaS: number;
  tempC: number | null;
  notes: string | null;
}

export interface GrindPass {
  id: number;
  millId: number;
  startedAt: string;
  passNo: number;
  durationMin: number;
  mediaType: string;
  operatorName: string;
}

export interface EnergyDaily {
  id: number;
  workshopId: number;
  workDate: string;
  kwh: number;
  peakKw: number | null;
}

export interface EnergyDailySummary {
  workshopId: number | null;
  startDate: string | null;
  endDate: string | null;
  totalKwh: number;
  maxPeakKw: number | null;
  dayCount: number;
}

export interface DashboardStats {
  workshopTotal: number;
  grindingMillCount: number;
  samplesLast24h: number;
  passesLast7d: number;
}
