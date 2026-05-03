"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/profile", label: "Profile" },
  { href: "/jobs", label: "Jobs" },
  { href: "/tracker", label: "Tracker" },
  { href: "/packets", label: "Packets" },
  { href: "/market", label: "Market" },
  { href: "/autofill", label: "Autofill" }
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="navbar" aria-label="Primary">
      <div className="navbar-brand">
        <strong>CareerAgent</strong>
        <span>Human-in-the-loop job search assistant</span>
      </div>

      <div className="nav-links">
        {navItems.map((item) => {
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link${isActive ? " active" : ""}`}
            >
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

