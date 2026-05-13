import { redirect } from "next/navigation";

export default async function AutofillPage({
  searchParams,
}: {
  searchParams: Promise<{ jobId?: string }>;
}) {
  const { jobId } = await searchParams;
  redirect(jobId ? `/apply?jobId=${jobId}` : "/apply");
}
