"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, Copy, Loader2, Pencil, Play, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { RunStatusBadge } from "./run-status-badge";
import { EditRunDialog } from "./edit-run-dialog";
import { DeleteRunDialog } from "./delete-run-dialog";
import { useCreateRun, useRun, useStartRun } from "@/lib/queries";
import type { FilterRun } from "@datacomp-image-text-filtering/shared";

function ConfigRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono tabular-nums">{value}</span>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="stat-value mt-1 text-xl">{value}</div>
    </div>
  );
}

export function RunDetail({ runId }: { runId: string }) {
  const { data: run, isLoading, error, refetch } = useRun(runId);
  const start = useStartRun();
  const clone = useCreateRun();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (error || !run) {
    return <ErrorState error={error ?? undefined} onRetry={() => refetch()} />;
  }

  const onStart = () =>
    start.mutate(run.id, {
      onSuccess: () => toast.success("Run started"),
      onError: (e) => toast.error("Couldn't start run", { description: e.message }),
    });

  const onClone = () =>
    clone.mutate(
      { ...run.config, name: `${run.config.name} (copy)` },
      {
        onSuccess: (created: FilterRun) => {
          toast.success("Cloned to a new pending run");
          router.push(`/runs/${created.id}`);
        },
        onError: (e) => toast.error("Couldn't clone run", { description: e.message }),
      }
    );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <Link
            href="/runs"
            className="mb-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3 w-3" /> All runs
          </Link>
          <div className="flex items-center gap-3">
            <h1 className="page-title truncate">{run.config.name}</h1>
            <RunStatusBadge status={run.status} />
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">id: {run.id}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {(run.status === "pending" || run.status === "failed") && (
            <Button size="sm" className="h-8" disabled={start.isPending} onClick={onStart}>
              <Play className="h-3.5 w-3.5" /> Start run
            </Button>
          )}
          {run.status === "pending" && (
            <Button size="sm" variant="outline" className="h-8" onClick={() => setEditing(true)}>
              <Pencil className="h-3.5 w-3.5" /> Edit
            </Button>
          )}
          {(run.status === "completed" || run.status === "running") && (
            <Button size="sm" variant="outline" className="h-8" disabled={clone.isPending} onClick={onClone}>
              <Copy className="h-3.5 w-3.5" /> Clone
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-destructive hover:text-destructive"
            onClick={() => setDeleting(true)}
          >
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </Button>
        </div>
      </div>

      {run.status === "running" && (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertTitle>Filtering in progress</AlertTitle>
          <AlertDescription>
            Streaming shards from B2 and scoring image-text alignment with CLIP.
            This view refreshes automatically.
          </AlertDescription>
        </Alert>
      )}

      {run.status === "failed" && run.error && (
        <Alert variant="destructive">
          <AlertTitle>Run failed</AlertTitle>
          <AlertDescription className="font-mono text-xs">{run.error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <ConfigRow label="Source pool" value={run.config.source_prefix} />
            <ConfigRow label="CLIP model" value={run.config.clip_model} />
            <ConfigRow label="Strategy" value={run.config.strategy} />
            <ConfigRow label="Keep fraction" value={run.config.clip_percentile} />
            <ConfigRow label="Min resolution" value={`${run.config.min_resolution}px`} />
            <ConfigRow
              label="Caption tokens"
              value={`${run.config.caption_min_tokens}–${run.config.caption_max_tokens}`}
            />
            <ConfigRow label="Dedup" value={run.config.dedup ? "on" : "off"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Results</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            {run.stats ? (
              <div className="grid grid-cols-2 gap-3">
                <StatTile label="Pairs kept" value={`${run.stats.total_pairs_kept} / ${run.stats.total_pairs_in}`} />
                <StatTile label="Storage reduction" value={`${run.stats.reduction_pct}%`} />
                <StatTile label="Mean CLIP score" value={run.stats.mean_clip_score} />
                <StatTile label="Score threshold" value={run.stats.clip_score_threshold ?? "—"} />
                <StatTile label="Device" value={run.stats.device ?? "—"} />
                <StatTile label="Shards" value={run.source_shard_count} />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No results yet — start the run to filter the pool.
              </p>
            )}
            {run.output_prefix && (
              <p className="mt-4 text-xs text-muted-foreground">
                Output shards under <code>{run.output_prefix}</code> · metrics under{" "}
                <code>{run.metrics_prefix}</code>. Inspect them in the{" "}
                <Link href="/pool" className="underline underline-offset-4">
                  Pool Explorer
                </Link>
                .
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {run.shard_metrics.length > 0 && (
        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Per-shard metrics</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Shard</TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">In</TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Kept</TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Dropped</TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Mean score</TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Kept mean</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {run.shard_metrics.map((m) => (
                  <TableRow key={m.shard} className="font-mono text-xs tabular-nums">
                    <TableCell>{m.shard}</TableCell>
                    <TableCell>{m.pairs_in}</TableCell>
                    <TableCell>{m.pairs_kept}</TableCell>
                    <TableCell>{m.pairs_dropped}</TableCell>
                    <TableCell>{m.mean_clip_score}</TableCell>
                    <TableCell>{m.kept_mean_clip_score}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {run.status === "pending" && (
        <EditRunDialog run={run} open={editing} onOpenChange={setEditing} />
      )}
      <DeleteRunDialog
        run={run}
        open={deleting}
        onOpenChange={setDeleting}
        onDeleted={() => router.push("/runs")}
      />
    </div>
  );
}
