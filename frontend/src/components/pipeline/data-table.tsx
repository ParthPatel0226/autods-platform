"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DataTableProps {
  data: Record<string, unknown>[];
  defaultRows?: number;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function DataTable({ data, defaultRows = 50 }: DataTableProps) {
  const [rowCount, setRowCount] = useState(
    Math.min(defaultRows, data.length),
  );

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No data to display.
      </p>
    );
  }

  const columns = Object.keys(data[0]);
  const visibleRows = data.slice(0, rowCount);

  return (
    <div className="flex flex-col gap-4">
      {/* Slider control */}
      <div className="flex items-center gap-4">
        <label className="text-xs text-muted-foreground whitespace-nowrap">
          Rows to display
        </label>
        <input
          type="range"
          min={5}
          max={Math.min(500, data.length)}
          step={5}
          value={rowCount}
          onChange={(e) => setRowCount(Number(e.target.value))}
          className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-white/15 accent-accent-violet"
        />
        <span className="w-14 text-right font-mono text-xs tabular-nums text-muted-foreground">
          {rowCount} / {data.length}
        </span>
      </div>

      {/* Table with horizontal scroll */}
      <div
        className={cn(
          "overflow-x-auto rounded-xl border border-white/8",
          "max-h-[480px] overflow-y-auto",
        )}
      >
        <Table className="min-w-max">
          <TableHeader className="sticky top-0 z-10 bg-cosmic-800">
            <TableRow className="border-white/8 bg-white/5">
              {columns.map((col) => (
                <TableHead
                  key={col}
                  className="text-xs font-mono uppercase tracking-widest text-muted-foreground"
                >
                  {col}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {visibleRows.map((row, i) => (
              <TableRow
                key={i}
                className="border-white/5 hover:bg-white/3"
              >
                {columns.map((col) => (
                  <TableCell
                    key={col}
                    className="py-1.5 font-mono text-xs text-muted-foreground max-w-[200px] truncate"
                  >
                    {String(row[col] ?? "—")}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
