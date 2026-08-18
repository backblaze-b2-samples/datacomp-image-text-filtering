import { RunDetail } from "@/components/runs/run-detail";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="animate-fade-in">
      <RunDetail runId={id} />
    </div>
  );
}
