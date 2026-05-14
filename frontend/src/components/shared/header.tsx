"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Settings, LogOut } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/hooks/useAuth";

// ─── Props ────────────────────────────────────────────────────────────────────

interface HeaderProps {
  projectName?: string;
  leftSlot?: React.ReactNode;
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Header({ projectName, leftSlot }: HeaderProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { setCurrentProject } = useAppStore();

  function handleLogoClick() {
    setCurrentProject(null);
    router.push("/projects");
  }

  const initials = user?.email
    ? user.email.charAt(0).toUpperCase()
    : "?";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-white/8 px-4">
      {/* Left: mobile menu trigger + brand + optional breadcrumb */}
      <div className="flex items-center gap-3">
        {leftSlot}
        <button
          onClick={handleLogoClick}
          className="font-display italic text-xl font-semibold glow-text leading-none hover:opacity-80 transition-opacity"
        >
          AutoDS
        </button>
        {projectName && (
          <>
            <span className="text-white/20 text-sm select-none">/</span>
            <span className="text-sm text-muted-foreground font-medium truncate max-w-[180px]">
              {projectName}
            </span>
          </>
        )}
      </div>

      {/* Right: user avatar + dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger
          className="rounded-full ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 hover:opacity-80"
          aria-label="User menu"
        >
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-accent-violet/20 text-accent-violet text-sm font-semibold border border-accent-violet/30">
              {initials}
            </AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end" className="w-52">
          {user?.email && (
            <div className="px-2 py-1.5">
              <p className="text-xs text-muted-foreground truncate">
                {user.email}
              </p>
            </div>
          )}
          <DropdownMenuSeparator />
          <DropdownMenuItem className="flex items-center gap-2 cursor-pointer p-0">
            <Link href="/settings" className="flex items-center gap-2 w-full px-2 py-1.5">
              <Settings className="h-4 w-4" />
              Settings
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={logout}
            className="flex items-center gap-2 text-destructive focus:text-destructive cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
