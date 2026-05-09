"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/profile", label: "Profile" },
  { href: "/jobs", label: "Jobs" },
  { href: "/applications", label: "Applications" },
  { href: "/insights", label: "Insights" },
  { href: "/settings", label: "Settings" }
];

const routeGroups: Record<string, string[]> = {
  "/profile": ["/profile", "/resume"],
  "/jobs": ["/jobs", "/job-finder"],
  "/applications": ["/applications", "/tracker", "/packets", "/autofill"],
  "/insights": ["/insights", "/market", "/predictions"],
  "/settings": ["/settings", "/ai"],
};

function isActiveNavItem(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }
  const group = routeGroups[href] || [href];
  return group.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export default function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="navbar" aria-label="Primary">
      <div className="navbar-brand">
        <Link href="/" className="brand">
          CareerAgent
        </Link>
        <span>Human-in-the-loop job search assistant</span>
      </div>

      <div className="nav-links">
        {navItems.map((item) => {
          const isActive = isActiveNavItem(pathname, item.href);

          return (
            <Link key={item.href} href={item.href} className={isActive ? "nav-link active" : "nav-link"}>
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
