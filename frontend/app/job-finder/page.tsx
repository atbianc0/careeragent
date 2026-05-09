import { redirect } from "next/navigation";

export default function JobFinderPage() {
  redirect("/jobs?tab=discover");
}
