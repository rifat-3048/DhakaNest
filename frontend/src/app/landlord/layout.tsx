import type { ReactNode } from "react";

import LandlordShell from "@/components/landlord/LandlordShell";

interface LandlordLayoutProps {
  children: ReactNode;
}

export default function LandlordLayout({ children }: LandlordLayoutProps) {
  return <LandlordShell>{children}</LandlordShell>;
}
