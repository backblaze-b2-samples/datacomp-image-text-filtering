"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Eye, Filter, Pencil, Play, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { RunStatusBadge } from "./run-status-badge";
import { EditRunDialog } from "./edit-run-dialog";
import { DeleteRunDialog } from "./delete-run-dialog";
import { CreateRunDialog } from "./create-run-dialog";
import { useRuns, useStartRun } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import type { FilterRun } from "@datacomp-image-text-filtering/shared";

export function RunsTable() {
  const { data: runs = [], isLoading, error, refetch } = useRuns();
  const start = useStartRun();
  const [editing, setEditing] = useState<FilterRun | null>(null);
  const [deleting, setDeleting] = useState<FilterRun | null>(null);

  const onStart = (run: FilterRun) =>
    start.mutate(run.id, {
      onSuccess: () => toast.success("Run started", { description: "Filtering the pool with CLIP…" }),
      onError: (e) => toast.error("Couldn't start run", { description: e.message }),
    });

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-3 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : runs.length === 0 ? (
          <EmptyState
            icon={Filter}
            title="No filter runs yet"
            description="Create a run to filter a pool of image-text shards by CLIP alignment."
            action={<CreateRunDialog label="Create your first run" />}
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Name</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Strategy</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Kept / In</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Reduction</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Created</TableHead>
                <TableHead className="text-right text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.map((run) => (
                <TableRow key={run.id} className="table-row-hover">
                  <TableCell className="font-medium">
                    <Link
                      href={`/runs/${run.id}`}
                      className="rounded-sm underline-offset-4 hover:underline"
                    >
                      {run.config.name}
                    </Link>
                    <span className="block text-xs text-muted-foreground">
                      {run.config.clip_model}
                    </span>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    <code className="text-xs">{run.config.strategy}</code>
                  </TableCell>
                  <TableCell>
                    <RunStatusBadge status={run.status} />
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                    {run.stats ? `${run.stats.total_pairs_kept} / ${run.stats.total_pairs_in}` : "—"}
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                    {run.stats ? `${run.stats.reduction_pct}%` : "—"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatDate(run.created_at)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-1">
                      {(run.status === "pending" || run.status === "failed") && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          title="Start run"
                          disabled={start.isPending}
                          onClick={() => onStart(run)}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                      )}
                      {run.status === "pending" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          title="Edit run"
                          onClick={() => setEditing(run)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      )}
                      <Button asChild variant="ghost" size="icon" className="h-8 w-8" title="View run">
                        <Link href={`/runs/${run.id}`}>
                          <Eye className="h-4 w-4" />
                        </Link>
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        title="Delete run"
                        onClick={() => setDeleting(run)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {editing && (
        <EditRunDialog
          run={editing}
          open={!!editing}
          onOpenChange={(open) => !open && setEditing(null)}
        />
      )}
      {deleting && (
        <DeleteRunDialog
          run={deleting}
          open={!!deleting}
          onOpenChange={(open) => !open && setDeleting(null)}
        />
      )}
    </Card>
  );
}
