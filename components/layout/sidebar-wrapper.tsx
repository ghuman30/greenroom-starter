"use client";

/**
 * Client wrapper around <Sidebar /> that hides it on public-facing
 * surfaces where the venue's internal nav would confuse a non-Greenroom
 * visitor — currently the agent confirmation page at /deal/[token].
 */

import { usePathname } from "next/navigation";
import { Sidebar } from "./sidebar";

const HIDE_ROOTS = ["/deal"];

export function SidebarWrapper() {
  const pathname = usePathname();
  // Anchor the match: hide on "/deal" exactly OR "/deal/..." but NOT
  // on something like "/dealings/..." that just happens to start with deal.
  const shouldHide = HIDE_ROOTS.some(
    (root) => pathname === root || pathname?.startsWith(`${root}/`),
  );
  if (shouldHide) return null;
  return <Sidebar />;
}
