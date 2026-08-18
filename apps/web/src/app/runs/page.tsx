import { CreateRunDialog } from "@/components/runs/create-run-dialog";
import { RunsTable } from "@/components/runs/runs-table";

export default function RunsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Filter Runs</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Create, run, and inspect DataComp-style CLIP filter jobs. Each run
            streams WebDataset shards from B2, scores image-text alignment, and
            writes filtered shards plus metrics back to B2.
          </p>
        </div>
        <CreateRunDialog />
      </div>
      <div className="animate-fade-in-up stagger-2">
        <RunsTable />
      </div>
    </div>
  );
}
