"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ApprovalDecision {
  label: string;
  value: string;
  alternatives?: string[];
}

interface ApprovalWidgetProps {
  title: string;
  decisions: ApprovalDecision[];
  reasoning: string;
  onApprove: () => void;
  onModify: (modified: Record<string, string>) => void;
  loading: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function ApprovalWidget({
  title,
  decisions,
  reasoning,
  onApprove,
  onModify,
  loading,
}: ApprovalWidgetProps) {
  const [editMode, setEditMode] = useState(false);
  const [reasoningOpen, setReasoningOpen] = useState(false);

  // Local modified values — keyed by decision label
  const originalValues = Object.fromEntries(
    decisions.map((d) => [d.label, d.value]),
  );
  const [modified, setModified] =
    useState<Record<string, string>>(originalValues);

  function handleReset() {
    setModified(originalValues);
    setEditMode(false);
  }

  function handleSave() {
    onModify(modified);
    setEditMode(false);
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Title */}
      <h1 className="text-2xl font-bold text-foreground">{title}</h1>

      {/* Decisions table */}
      <div className="rounded-2xl border border-white/8 bg-white/2 overflow-hidden backdrop-blur-sm">
        <Table>
          <TableHeader>
            <TableRow className="border-white/8 bg-white/5">
              <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground w-1/2">
                Decision
              </TableHead>
              <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
                Proposed Value
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {decisions.map((d) => (
              <TableRow key={d.label} className="border-white/5 hover:bg-white/3">
                <TableCell className="text-sm text-foreground font-medium">
                  {d.label}
                </TableCell>
                <TableCell>
                  {editMode && d.alternatives && d.alternatives.length > 0 ? (
                    <Select
                      value={modified[d.label] ?? d.value}
                      onValueChange={(v) =>
                        setModified((prev) => ({ ...prev, [d.label]: v ?? d.value }))
                      }
                    >
                      <SelectTrigger className="w-full max-w-[240px] h-7 text-xs bg-white/5 border-white/15 hover:border-accent-violet/60">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {/* Always include current value */}
                        {[d.value, ...d.alternatives.filter((a) => a !== d.value)].map(
                          (alt) => (
                            <SelectItem key={alt} value={alt}>
                              {alt}
                            </SelectItem>
                          ),
                        )}
                      </SelectContent>
                    </Select>
                  ) : (
                    <span className="text-sm font-mono text-accent-violet">
                      {modified[d.label] ?? d.value}
                    </span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* AI Reasoning collapsible */}
      <Collapsible open={reasoningOpen} onOpenChange={setReasoningOpen}>
        <CollapsibleTrigger
          className={cn(
            "flex w-full items-center justify-between rounded-xl",
            "border border-white/8 bg-white/2 px-4 py-3",
            "text-sm font-medium text-foreground",
            "hover:bg-white/5 transition-colors cursor-pointer",
          )}
        >
          <span>View AI reasoning</span>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform duration-200",
              reasoningOpen && "rotate-180",
            )}
          />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="mt-2 rounded-xl border border-white/8 bg-white/3 px-5 py-4 backdrop-blur-sm">
            <p className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap">
              {reasoning}
            </p>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Action buttons */}
      <div className="flex gap-3">
        {editMode ? (
          <>
            {/* Save & Apply */}
            <button
              type="button"
              disabled={loading}
              onClick={handleSave}
              className={cn(
                "btn-glow flex flex-1 items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold",
                loading && "opacity-50 cursor-not-allowed",
              )}
            >
              {loading && (
                <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              )}
              Save & Apply
            </button>

            {/* Reset */}
            <Button
              variant="outline"
              disabled={loading}
              onClick={handleReset}
              className="flex-1 rounded-xl px-5 py-3 text-sm font-semibold h-auto border-white/15 text-foreground hover:bg-white/5"
            >
              Reset
            </Button>
          </>
        ) : (
          <>
            {/* Approve & Continue */}
            <button
              type="button"
              disabled={loading}
              onClick={onApprove}
              className={cn(
                "btn-glow flex flex-1 items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold",
                loading && "opacity-50 cursor-not-allowed",
              )}
            >
              {loading && (
                <span className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              )}
              Approve & Continue
            </button>

            {/* Modify */}
            <Button
              variant="outline"
              disabled={loading}
              onClick={() => setEditMode(true)}
              className="flex-1 rounded-xl px-5 py-3 text-sm font-semibold h-auto border-white/15 text-foreground hover:bg-white/5"
            >
              Modify
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
