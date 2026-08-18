import { PoolExplorer } from "@/components/pool/pool-explorer";

export default function PoolPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Pool Explorer</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          Inspect the image-text pairs inside a WebDataset shard. Scoped to the
          raw <code>pool/</code> and filtered <code>filtered/</code> prefixes —
          open a shard to see each pair&apos;s thumbnail, caption, CLIP score, and
          kept/dropped decision.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <PoolExplorer />
      </div>
    </div>
  );
}
