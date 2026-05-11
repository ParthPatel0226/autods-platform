"use client";

import Link from "next/link";
import { Telescope } from "lucide-react";

export default function NotFound() {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden aurora-bg">
      {/* Faint grid overlay */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(139,92,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(139,92,246,0.03)_1px,transparent_1px)] bg-[size:48px_48px]"
      />

      <div className="relative flex flex-col items-center gap-8 text-center px-6">
        {/* Icon */}
        <div className="rounded-2xl border border-white/8 bg-white/4 p-6 backdrop-blur-sm">
          <Telescope
            className="h-12 w-12 text-accent-violet"
            strokeWidth={1.5}
          />
        </div>

        {/* 404 badge */}
        <p className="text-xs font-mono uppercase tracking-widest text-accent-violet bg-accent-violet/10 border border-accent-violet/20 rounded-full px-3 py-1">
          404
        </p>

        {/* Heading */}
        <div className="flex flex-col gap-2">
          <h1 className="font-display italic text-4xl font-bold text-foreground">
            Lost in the cosmos?
          </h1>
          <p className="text-base text-muted-foreground max-w-sm leading-relaxed">
            The page you&apos;re looking for doesn&apos;t exist or has drifted
            into a black hole.
          </p>
        </div>

        {/* Action */}
        <Link
          href="/projects"
          className="btn-glow inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium"
        >
          Back to Projects
        </Link>
      </div>
    </div>
  );
}
