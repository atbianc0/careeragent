import { redirect } from "next/navigation";

export default function TrackerPage() {
  redirect("/insights?tab=tracker");
}
