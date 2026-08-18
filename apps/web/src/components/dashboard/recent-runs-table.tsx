"use client";

import Link from "next/link";
import { ArrowRight, Filter } from "lucide-react";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { RunStatusBadge } from "@/components/runs/run-status-badge";
import { CreateRunDialog } from "@/components/runs/create-run-dialog";
import { useRuns } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function RecentRunsTable() {
  const { data: runs = [], isLoading, error, refetch } = useRuns();
  const recent = runs.slice(0, 6);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Runs</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/runs"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="space-y-3 p-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={Filter}
            title="No runs yet"
            description="Create a filter run to curate a pool of image-text shards."
            action={<CreateRunDialog label="Create your first run" />}
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Name</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Reduction</TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((run) => (
                <TableRow key={run.id} className="table-row-hover">
                  <TableCell className="font-medium">
                    <Link
                      href={`/runs/${run.id}`}
                      className="block truncate rounded-sm underline-offset-4 hover:underline"
                    >
                      {run.config.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <RunStatusBadge status={run.status} />
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                    {run.stats ? `${run.stats.reduction_pct}%` : "—"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {formatDate(run.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
