"use client";

import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ColumnInfo {
  name: string;
  type: string;
  missing_pct: number;
  unique: number;
  sample: unknown;
}

interface DataPreviewTableProps {
  columns: ColumnInfo[];
}

// ─── Type badge ───────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  int64: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  int32: "bg-blue-500/15 text-blue-400 border-blue-500/20",
  float64: "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",
  float32: "bg-cyan-500/15 text-cyan-400 border-cyan-500/20",
  object: "bg-violet-500/15 text-violet-400 border-violet-500/20",
  datetime64: "bg-pink-500/15 text-pink-400 border-pink-500/20",
  bool: "bg-amber-500/15 text-amber-400 border-amber-500/20",
  category: "bg-green-500/15 text-green-400 border-green-500/20",
};

function typeBadgeClass(type: string): string {
  // match prefix (e.g. "datetime64[ns]" → "datetime64")
  for (const key of Object.keys(TYPE_COLORS)) {
    if (type.startsWith(key)) return TYPE_COLORS[key];
  }
  return "bg-white/10 text-white/60 border-white/10";
}

// ─── Missing% bar ─────────────────────────────────────────────────────────────

function MissingBar({ pct }: { pct: number }) {
  const color =
    pct < 5
      ? "bg-accent-green"
      : pct < 20
        ? "bg-amber-400"
        : "bg-red-400";

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/10">
        <div
          className={cn("h-full rounded-full transition-all", color)}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DataPreviewTable({ columns }: DataPreviewTableProps) {
  return (
    <div className="rounded-xl border border-white/8 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="border-white/8 bg-white/5">
            <TableHead className="text-xs uppercase tracking-widest text-muted-foreground">
              Column Name
            </TableHead>
            <TableHead className="text-xs uppercase tracking-widest text-muted-foreground">
              Type
            </TableHead>
            <TableHead className="text-xs uppercase tracking-widest text-muted-foreground">
              Missing %
            </TableHead>
            <TableHead className="text-xs uppercase tracking-widest text-muted-foreground">
              Unique
            </TableHead>
            <TableHead className="text-xs uppercase tracking-widest text-muted-foreground">
              Sample
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {columns.map((col) => (
            <TableRow
              key={col.name}
              className="border-white/5 hover:bg-white/3"
            >
              <TableCell className="py-2 font-mono text-xs font-medium">
                {col.name}
              </TableCell>
              <TableCell className="py-2">
                <span
                  className={cn(
                    "inline-block rounded-full border px-2 py-0.5 font-mono text-[10px]",
                    typeBadgeClass(col.type),
                  )}
                >
                  {col.type}
                </span>
              </TableCell>
              <TableCell className="py-2">
                <MissingBar pct={col.missing_pct} />
              </TableCell>
              <TableCell className="py-2 font-mono text-xs text-muted-foreground">
                {col.unique.toLocaleString()}
              </TableCell>
              <TableCell className="py-2 max-w-[160px] truncate font-mono text-xs text-muted-foreground">
                {String(col.sample ?? "—")}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
