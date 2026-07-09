import { Dashboard } from "@/components/auth/Dashboard";

export default function AdminDashboardPage() {
  return <Dashboard requiredRole="admin" title="Welcome Admin" />;
}
