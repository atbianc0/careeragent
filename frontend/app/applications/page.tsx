import { redirect } from "next/navigation";

export default async function ApplicationsPage({
  searchParams,
}: {
  searchParams: Promise<{ jobId?: string }>;
}) {
  const params = await searchParams;
  redirect(params.jobId ? `/apply?jobId=${params.jobId}` : "/apply");
}
