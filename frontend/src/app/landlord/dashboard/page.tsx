import { Dashboard } from "@/components/auth/Dashboard";

export default function LandlordDashboardPage() {
  return <Dashboard requiredRole="landlord" title="Welcome Landlord" />;
}
