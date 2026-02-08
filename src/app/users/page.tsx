"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getUsers, type UserListItem } from "@/lib/api";

export default function UsersPage() {
  return (
    <Suspense fallback={<div className="p-6"><Skeleton className="h-8 w-48" /></div>}>
      <UsersPageInner />
    </Suspense>
  );
}

function UsersPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [users, setUsers] = useState<UserListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(Number(searchParams.get("page")) || 1);
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [searchInput, setSearchInput] = useState(
    searchParams.get("search") || ""
  );
  const [hasProfile, setHasProfile] = useState<boolean | undefined>(
    searchParams.get("has_profile") === "true" ? true : undefined
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const pageSize = 50;

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getUsers(page, pageSize, search || undefined, hasProfile);
      setUsers(data.users);
      setTotal(data.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [page, search, hasProfile]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const totalPages = Math.ceil(total / pageSize);

  function handleSearch() {
    setSearch(searchInput);
    setPage(1);
  }

  function arcColor(arc: string | null) {
    if (!arc) return "secondary";
    if (arc === "growth") return "default";
    if (arc === "stable") return "secondary";
    if (arc === "declining" || arc === "churn") return "destructive";
    return "outline";
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Browse and search user profiles. {total.toLocaleString()} total users.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Input
            placeholder="Search by user ID..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="h-9 bg-secondary/50"
          />
        </div>
        <Button variant="secondary" size="sm" onClick={handleSearch}>
          Search
        </Button>
        <Button
          variant={hasProfile ? "default" : "outline"}
          size="sm"
          onClick={() => {
            setHasProfile(hasProfile ? undefined : true);
            setPage(1);
          }}
        >
          Profiled Only
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="text-xs">User ID</TableHead>
                <TableHead className="text-xs">Temperament</TableHead>
                <TableHead className="text-xs">Arc</TableHead>
                <TableHead className="text-xs">Language</TableHead>
                <TableHead className="text-xs text-right">
                  Conversations
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading
                ? Array.from({ length: 10 }).map((_, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <Skeleton className="h-4 w-48" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-20" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-16" />
                      </TableCell>
                      <TableCell>
                        <Skeleton className="h-4 w-16" />
                      </TableCell>
                      <TableCell className="text-right">
                        <Skeleton className="h-4 w-8 ml-auto" />
                      </TableCell>
                    </TableRow>
                  ))
                : users.map((user) => (
                    <TableRow
                      key={user.user_id}
                      className="cursor-pointer"
                      onClick={() => router.push(`/users/${user.user_id}`)}
                    >
                      <TableCell className="font-mono text-xs">
                        {user.user_id.slice(0, 8)}...
                      </TableCell>
                      <TableCell>
                        {user.temperament_label ? (
                          <div className="flex items-center gap-2">
                            <span className="text-sm capitalize">
                              {user.temperament_label}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {user.temperament_score}/10
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        {user.current_arc ? (
                          <Badge variant={arcColor(user.current_arc) as "default" | "secondary" | "destructive" | "outline"} className="text-xs">
                            {user.current_arc}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            —
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {user.primary_language || "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-sm">
                        {user.total_conversations ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
