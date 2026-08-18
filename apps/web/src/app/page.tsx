import { RunStatsCards } from "@/components/dashboard/run-stats-cards";
import { RecentRunsTable } from "@/components/dashboard/recent-runs-table";
import { CreateRunDialog } from "@/components/runs/create-run-dialog";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5 max-w-prose">
            DataComp-style image-text dataset curation on Backblaze B2. Filter
            WebDataset shards by CLIP alignment — B2 is the sole store for the raw
            pool, filtered output, and quality metrics.
          </p>
        </div>
        <CreateRunDialog />
      </div>
      <RunStatsCards />
      <div className="animate-fade-in-up stagger-3">
        <RecentRunsTable />
      </div>
    </div>
  );
}
