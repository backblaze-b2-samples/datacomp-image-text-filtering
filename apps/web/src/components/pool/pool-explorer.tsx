"use client";

import { useState } from "react";
import { Boxes, PackageOpen } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePoolShard, usePoolShards } from "@/lib/queries";
import type { ShardSummary } from "@datacomp-image-text-filtering/shared";

function ShardList({
  scope,
  selected,
  onSelect,
}: {
  scope: "pool" | "filtered";
  selected: string | undefined;
  onSelect: (s: ShardSummary) => void;
}) {
  const { data: shards = [], isLoading, error, refetch } = usePoolShards(scope);

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading) {
    return (
      <div className="space-y-2 p-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    );
  }
  if (shards.length === 0) {
    return (
      <EmptyState
        icon={Boxes}
        title={scope === "pool" ? "No raw shards" : "No filtered shards"}
        description={
          scope === "pool"
            ? "Seed a pool: services/api/scripts/seed_pool.py"
            : "Run a filter to produce output shards."
        }
      />
    );
  }
  return (
    <ul className="divide-y divide-border">
      {shards.map((shard) => (
        <li key={shard.key}>
          <button
            type="button"
            onClick={() => onSelect(shard)}
            className={`flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left text-sm hover:bg-accent ${
              selected === shard.key ? "bg-accent font-medium" : ""
            }`}
          >
            <span className="truncate font-mono text-xs">{shard.name}</span>
            <span className="shrink-0 text-xs text-muted-foreground">
              {shard.size_human}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function PairsGrid({ shardKey }: { shardKey: string }) {
  const { data, isLoading, error, refetch } = usePoolShard(shardKey);

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 md:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="aspect-square w-full" />
        ))}
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="p-4">
      <p className="mb-3 text-xs text-muted-foreground">
        Showing {data.shown} of {data.pair_count} pairs in{" "}
        <code>{data.key}</code>
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        {data.pairs.map((pair) => (
          <figure
            key={pair.key}
            className="overflow-hidden rounded-md border border-border"
          >
            <div className="relative aspect-square bg-muted">
              {pair.thumbnail_data_url ? (
                // eslint-disable-next-line @next/next/no-img-element -- data URL, not a remote asset
                <img
                  src={pair.thumbnail_data_url}
                  alt={pair.caption}
                  className="h-full w-full object-contain"
                />
              ) : null}
              {pair.kept !== null && (
                <Badge
                  variant={pair.kept ? "default" : "destructive"}
                  className="absolute right-1.5 top-1.5"
                >
                  {pair.kept ? "kept" : "dropped"}
                </Badge>
              )}
            </div>
            <figcaption className="space-y-1 p-2">
              <p className="line-clamp-2 text-xs" title={pair.caption}>
                {pair.caption}
              </p>
              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span>
                  {pair.width && pair.height ? `${pair.width}×${pair.height}` : "—"}
                </span>
                {pair.clip_score !== null && (
                  <span className="font-mono">CLIP {pair.clip_score}</span>
                )}
              </div>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}

export function PoolExplorer() {
  const [scope, setScope] = useState<"pool" | "filtered">("pool");
  const [selected, setSelected] = useState<ShardSummary | undefined>(undefined);

  return (
    <div className="space-y-4">
      <Tabs
        value={scope}
        onValueChange={(v) => {
          setScope(v as "pool" | "filtered");
          setSelected(undefined);
        }}
      >
        <TabsList>
          <TabsTrigger value="pool">Pool (raw)</TabsTrigger>
          <TabsTrigger value="filtered">Filtered (output)</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <Card className="h-fit">
          <CardHeader className="border-b border-border py-3 px-4">
            <CardTitle className="card-title text-sm">Shards</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ShardList
              scope={scope}
              selected={selected?.key}
              onSelect={setSelected}
            />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-0">
            {selected ? (
              <PairsGrid shardKey={selected.key} />
            ) : (
              <EmptyState
                icon={PackageOpen}
                title="Open a shard"
                description="Select a shard to view the image-text pairs inside it — thumbnail, caption, CLIP score, and kept/dropped."
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
