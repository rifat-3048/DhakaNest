import { Dashboard } from "@/components/auth/Dashboard";

export default function TenantDashboardPage() {
  return <Dashboard requiredRole="tenant" title="Welcome Tenant" />;
}
