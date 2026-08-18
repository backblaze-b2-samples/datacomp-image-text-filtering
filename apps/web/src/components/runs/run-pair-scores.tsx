"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useRunPairs } from "@/lib/queries";

/**
 * Per-pair kept-vs-dropped detail for a completed run.
 *
 * The filtered `.tar` shards hold only KEPT pairs, so the Pool Explorer can
 * never show a dropped pair. This table reads the run's `metrics/<id>/*.json`
 * (which records every scored pair) so a first-time user can finally see which
 * pairs CLIP dropped and their low scores — sorted by score, with the keep
 * threshold shown, so the kept/dropped boundary is obvious.
 */
export function RunPairScores({
  runId,
  enabled,
}: {
  runId: string;
  enabled: boolean;
}) {
  const { data, isLoading, error, refetch } = useRunPairs(runId, enabled);

  if (!enabled) return null;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Per-pair CLIP scores</CardTitle>
        {data && data.pair_count > 0 && (
          <p className="mt-1 text-xs text-muted-foreground">
            {data.pair_count} scored pairs — kept vs dropped.
            {data.clip_score_threshold !== null && (
              <>
                {" "}
                Keep threshold{" "}
                <span className="font-mono">{data.clip_score_threshold}</span>.
              </>
            )}
          </p>
        )}
      </CardHeader>
      <CardContent className="p-0">
        {error ? (
          <div className="p-5">
            <ErrorState error={error} onRetry={() => refetch()} />
          </div>
        ) : isLoading ? (
          <div className="space-y-2 p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : !data || data.pair_count === 0 ? (
          <p className="p-5 text-sm text-muted-foreground">
            No per-pair metrics for this run yet.
          </p>
        ) : (
          <div className="max-h-[28rem] overflow-auto">
            <Table>
              <TableHeader className="sticky top-0 bg-background">
                <TableRow className="bg-muted/40 hover:bg-muted/40">
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Caption
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Shard
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    CLIP score
                  </TableHead>
                  <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Decision
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.pairs.map((pair) => (
                  <TableRow key={`${pair.shard}/${pair.key}`} className="text-xs">
                    <TableCell
                      className="max-w-[24rem] truncate"
                      title={pair.caption}
                    >
                      {pair.caption}
                    </TableCell>
                    <TableCell className="font-mono text-muted-foreground">
                      {pair.shard}
                    </TableCell>
                    <TableCell className="font-mono tabular-nums">
                      {pair.clip_score}
                    </TableCell>
                    <TableCell>
                      <Badge variant={pair.kept ? "default" : "destructive"}>
                        {pair.kept ? "kept" : "dropped"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
