"use client";

import { cn } from "@/lib/utils";
import type { EDAQuestion, EDAQuestionOption } from "@/lib/api/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// ─── Types ────────────────────────────────────────────────────────────────────

interface QuestionRendererProps {
  question: EDAQuestion;
  value: unknown;
  onChange: (value: unknown) => void;
}

// Column schema passed via question.options when type === "per_column_table"
// Each option.value = column name, option.label = dtype
// question.options themselves become the strategy choices when flattened

// ─── Sub-renderers ────────────────────────────────────────────────────────────

function SingleSelect({
  options = [],
  value,
  onChange,
}: {
  options: EDAQuestionOption[];
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const recommended = options.find((o) => o.recommended);

  return (
    <Select value={String(value ?? "")} onValueChange={onChange}>
      <SelectTrigger className="w-full bg-white/5 border-white/15 text-foreground hover:border-accent-violet/60 transition-colors">
        <SelectValue placeholder="Select an option…" />
      </SelectTrigger>
      <SelectContent>
        {options.map((opt) => (
          <SelectItem key={opt.value} value={opt.value}>
            {opt.recommended ? "⭐ " : ""}
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function MultiSelect({
  options = [],
  value,
  onChange,
}: {
  options: EDAQuestionOption[];
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const selected: string[] = Array.isArray(value) ? (value as string[]) : [];

  function toggle(optValue: string) {
    const next = selected.includes(optValue)
      ? selected.filter((v) => v !== optValue)
      : [...selected, optValue];
    onChange(next);
  }

  function selectRecommended() {
    const rec = options.filter((o) => o.recommended).map((o) => o.value);
    onChange(rec);
  }

  const hasRecommended = options.some((o) => o.recommended);

  return (
    <div className="flex flex-col gap-2">
      {hasRecommended && (
        <button
          type="button"
          onClick={selectRecommended}
          className="self-start text-xs font-mono text-accent-violet hover:text-accent-violet/80 transition-colors"
        >
          ⭐ Select recommended
        </button>
      )}
      <div className="rounded-xl border border-white/10 bg-white/3 backdrop-blur-sm divide-y divide-white/5">
        {options.map((opt) => (
          <label
            key={opt.value}
            className={cn(
              "flex items-center gap-3 px-4 py-2.5 cursor-pointer",
              "hover:bg-white/5 transition-colors",
              selected.includes(opt.value) && "bg-accent-violet/8",
            )}
          >
            <input
              type="checkbox"
              checked={selected.includes(opt.value)}
              onChange={() => toggle(opt.value)}
              className="h-4 w-4 rounded border-white/20 bg-white/10 accent-accent-violet cursor-pointer"
            />
            <span className="text-sm text-foreground">
              {opt.recommended && <span className="mr-1">⭐</span>}
              {opt.label}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

function SliderInput({
  question,
  value,
  onChange,
}: {
  question: EDAQuestion;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  // Derive min/max/step from options if provided, else sensible defaults
  const opts = question.options ?? [];
  const min = opts[0] ? Number(opts[0].value) : 0;
  const max = opts[1] ? Number(opts[1].value) : 100;
  const step = opts[2] ? Number(opts[2].value) : 1;
  const current = typeof value === "number" ? value : min;

  return (
    <div className="flex flex-col gap-3">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={current}
        onChange={(e) => onChange(Number(e.target.value))}
        className={cn(
          "h-1.5 w-full cursor-pointer appearance-none rounded-full",
          "bg-white/15 accent-accent-violet",
          "[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4",
          "[&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent-violet",
          "[&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(168,85,247,0.6)]",
        )}
      />
      <div className="flex justify-between text-xs font-mono text-muted-foreground">
        <span>{min}</span>
        <span className="text-accent-violet font-semibold">{current}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

function TextInput({
  question,
  value,
  onChange,
}: {
  question: EDAQuestion;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  return (
    <Input
      value={typeof value === "string" ? value : ""}
      onChange={(e) => onChange(e.target.value)}
      placeholder={question.recommendation_reason ?? "Type your answer…"}
      className="bg-white/5 border-white/15 focus:border-accent-violet/60"
    />
  );
}

function NumberInput({
  question,
  value,
  onChange,
}: {
  question: EDAQuestion;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const opts = question.options ?? [];
  const min = opts[0] ? Number(opts[0].value) : undefined;
  const max = opts[1] ? Number(opts[1].value) : undefined;

  return (
    <Input
      type="number"
      value={typeof value === "number" ? value : ""}
      onChange={(e) => onChange(e.target.valueAsNumber)}
      min={min}
      max={max}
      placeholder="Enter a number…"
      className="bg-white/5 border-white/15 focus:border-accent-violet/60 w-48"
    />
  );
}

/**
 * per_column_table renderer.
 *
 * question.options = the list of STRATEGY choices (e.g. mean, median, mode…)
 *
 * The column metadata (name + dtype) must be supplied via the `value` prop as
 * an object with shape:
 *   { columns: Array<{ name: string; dtype: string }>, selections: Record<string, string> }
 *
 * On every strategy change we call onChange with the updated `selections` map
 * (Record<column_name, strategy_value>).
 */
function PerColumnTable({
  options = [],
  value,
  onChange,
}: {
  options: EDAQuestionOption[];
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  type TableValue = {
    columns: Array<{ name: string; dtype: string }>;
    selections: Record<string, string>;
  };

  const tv = value as TableValue | null;
  const columns = tv?.columns ?? [];
  const selections = tv?.selections ?? {};

  function handleStrategy(colName: string, strategy: string) {
    const next: Record<string, string> = { ...selections, [colName]: strategy };
    onChange({ columns, selections: next });
  }

  if (columns.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No column data available.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-white/10">
      <Table>
        <TableHeader>
          <TableRow className="border-white/8 bg-white/5">
            <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground w-1/3">
              Column
            </TableHead>
            <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground w-1/4">
              Type
            </TableHead>
            <TableHead className="text-xs font-mono uppercase tracking-widest text-muted-foreground">
              Strategy
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {columns.map((col) => (
            <TableRow key={col.name} className="border-white/5 hover:bg-white/3">
              <TableCell className="font-mono text-xs text-foreground">
                {col.name}
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {col.dtype}
              </TableCell>
              <TableCell>
                <Select
                  value={selections[col.name] ?? ""}
                  onValueChange={(v) => { if (v !== null) handleStrategy(col.name, v); }}
                >
                  <SelectTrigger className="w-full max-w-[180px] h-7 text-xs bg-white/5 border-white/15 hover:border-accent-violet/60">
                    <SelectValue placeholder="Choose…" />
                  </SelectTrigger>
                  <SelectContent>
                    {options.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ─── Question wrapper ─────────────────────────────────────────────────────────

function QuestionWrapper({
  question,
  children,
}: {
  question: EDAQuestion;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/3 backdrop-blur-sm p-4 flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-foreground leading-snug">
          {question.question}
        </p>
        {question.domain_specific && (
          <span className="shrink-0 inline-flex items-center rounded-md border border-accent-violet/40 bg-accent-violet/10 px-2 py-0.5 text-[10px] font-mono text-accent-violet">
            domain
          </span>
        )}
      </div>

      {/* Widget */}
      {children}

      {/* Helper */}
      {question.recommendation_reason && (
        <p className="text-xs text-muted-foreground leading-relaxed">
          {question.recommendation_reason}
        </p>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function QuestionRenderer({
  question,
  value,
  onChange,
}: QuestionRendererProps) {
  const opts = question.options ?? [];

  function renderWidget() {
    switch (question.type) {
      case "single_select":
        return (
          <SingleSelect options={opts} value={value} onChange={onChange} />
        );

      case "multi_select":
        return (
          <MultiSelect options={opts} value={value} onChange={onChange} />
        );

      case "slider":
        return (
          <SliderInput question={question} value={value} onChange={onChange} />
        );

      case "text_input":
        return (
          <TextInput question={question} value={value} onChange={onChange} />
        );

      case "number_input":
        return (
          <NumberInput question={question} value={value} onChange={onChange} />
        );

      case "per_column_table":
        return (
          <PerColumnTable options={opts} value={value} onChange={onChange} />
        );

      default:
        return (
          <p className="text-xs text-muted-foreground font-mono">
            Unknown question type: {question.type}
          </p>
        );
    }
  }

  return (
    <QuestionWrapper question={question}>{renderWidget()}</QuestionWrapper>
  );
}
