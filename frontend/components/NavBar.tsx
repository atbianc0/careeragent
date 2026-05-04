"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/profile", label: "Profile" },
  { href: "/resume", label: "Resume" },
  { href: "/jobs", label: "Jobs" },
  { href: "/tracker", label: "Tracker" },
  { href: "/packets", label: "Packets" },
  { href: "/market", label: "Market" },
  { href: "/predictions", label: "Predictions" },
  { href: "/ai", label: "AI" },
  { href: "/autofill", label: "Autofill" }
];

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
          const isActive = item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(`${item.href}/`);

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
