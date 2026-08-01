import type { ReactNode } from "react";

import TenantShell from "@/components/tenant/TenantShell";

export default function TenantLayout({ children }: { children: ReactNode }) {
  return <TenantShell>{children}</TenantShell>;
}
