"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getProfile, getAdaptationPreview, type Profile, type AdaptationPreview } from "@/lib/api";

function ScoreBar({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-xs font-mono font-medium">{Math.round(value)}</span>
      </div>
      <Progress value={value} className="h-1.5" />
    </div>
  );
}

function StyleDimension({ label, value }: { label: string; value: number }) {
  const percentage = Math.round(value * 100);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-xs font-mono">{percentage}%</span>
      </div>
      <div className="h-1 rounded-full bg-secondary">
        <div
          className="h-full rounded-full bg-foreground/60 transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const params = useParams();
  const router = useRouter();
  const userId = params.id as string;

  const [profile, setProfile] = useState<Profile | null>(null);
  const [adaptation, setAdaptation] = useState<AdaptationPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    Promise.all([
      getProfile(userId).catch(() => null),
      getAdaptationPreview(userId).catch(() => null),
    ])
      .then(([p, a]) => {
        if (!p) {
          setError("Profile not found");
        } else {
          setProfile(p);
          setAdaptation(a);
        }
      })
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-12">
        <p className="text-muted-foreground">{error || "Profile not found"}</p>
        <Button variant="outline" size="sm" onClick={() => router.push("/users")}>
          Back to Users
        </Button>
      </div>
    );
  }

  const temp = profile.temperament;
  const style = profile.communication_style;
  const sentiment = profile.sentiment_trend;
  const lifeStage = profile.life_stage;
  const topics = profile.topic_interests;
  const scores = profile.scores;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">
              User Profile
            </h1>
            {profile.current_arc && (
              <Badge variant="outline" className="text-xs">
                {profile.current_arc}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground font-mono mt-1">
            {profile.user_id}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push(`/chat?user_id=${userId}`)}
          >
            Chat as User
          </Button>
          <Button variant="outline" size="sm" onClick={() => router.push("/users")}>
            Back
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList className="bg-secondary/50">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="scores">Fit Scores</TabsTrigger>
          <TabsTrigger value="adaptation">Adaptation</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Temperament */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">Temperament</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {temp ? (
                  <>
                    <div className="flex items-center gap-3">
                      <div className="text-3xl font-bold tabular-nums">
                        {temp.score}
                      </div>
                      <div>
                        <div className="text-sm font-medium capitalize">
                          {temp.label}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Volatility: {temp.volatility}
                        </div>
                      </div>
                    </div>
                    <div className="h-1.5 rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full bg-foreground/50 transition-all"
                        style={{ width: `${(temp.score / 10) * 100}%` }}
                      />
                    </div>
                    {temp.summary && (
                      <p className="text-xs text-muted-foreground">
                        {temp.summary}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-xs text-muted-foreground">No data</p>
                )}
              </CardContent>
            </Card>

            {/* Communication Style */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">
                  Communication Style
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {style ? (
                  <>
                    <StyleDimension label="Formality" value={style.formality} />
                    <StyleDimension label="Verbosity" value={style.verbosity} />
                    <StyleDimension
                      label="Technicality"
                      value={style.technicality}
                    />
                    <StyleDimension label="Structured" value={style.structured} />
                    {style.summary && (
                      <p className="text-xs text-muted-foreground mt-2">
                        {style.summary}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-xs text-muted-foreground">No data</p>
                )}
              </CardContent>
            </Card>

            {/* Sentiment */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">
                  Sentiment Trend
                </CardTitle>
              </CardHeader>
              <CardContent>
                {sentiment ? (
                  <div className="space-y-3">
                    <div className="flex items-center gap-4">
                      <Badge variant="outline" className="text-xs capitalize">
                        {sentiment.direction}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        Recent avg:{" "}
                        <span className="font-mono">
                          {sentiment.recent_avg.toFixed(2)}
                        </span>
                      </span>
                    </div>
                    {sentiment.frustration_rate > 0 && (
                      <div className="text-xs text-destructive">
                        Frustration rate:{" "}
                        {(sentiment.frustration_rate * 100).toFixed(0)}%
                      </div>
                    )}
                    {sentiment.summary && (
                      <p className="text-xs text-muted-foreground">
                        {sentiment.summary}
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No data</p>
                )}
              </CardContent>
            </Card>

            {/* Life Stage & Topics */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium">
                  Life Stage & Interests
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {lifeStage && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium capitalize">
                        {lifeStage.stage}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        ({(lifeStage.confidence * 100).toFixed(0)}% confidence)
                      </span>
                    </div>
                    {lifeStage.domain_expertise.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {lifeStage.domain_expertise.map((d) => (
                          <Badge key={d} variant="secondary" className="text-xs">
                            {d}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {topics && (
                  <>
                    <Separator />
                    <div className="space-y-2">
                      <div className="text-xs font-medium text-muted-foreground">
                        Topics
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {topics.primary.map((t) => (
                          <Badge key={t} variant="default" className="text-xs">
                            {t}
                          </Badge>
                        ))}
                        {topics.secondary.map((t) => (
                          <Badge key={t} variant="outline" className="text-xs">
                            {t}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Meta info */}
          <Card>
            <CardContent className="py-4">
              <div className="flex flex-wrap gap-x-8 gap-y-2 text-xs text-muted-foreground">
                <span>
                  Language:{" "}
                  <span className="text-foreground">
                    {profile.primary_language || "Unknown"}
                  </span>
                </span>
                <span>
                  Version:{" "}
                  <span className="text-foreground font-mono">
                    {profile.profile_version}
                  </span>
                </span>
                {profile.updated_at && (
                  <span>
                    Updated:{" "}
                    <span className="text-foreground">
                      {new Date(profile.updated_at).toLocaleDateString()}
                    </span>
                  </span>
                )}
                {profile.interaction_stats && (
                  <>
                    <span>
                      Conversations analyzed:{" "}
                      <span className="text-foreground font-mono">
                        {profile.interaction_stats.total_conversations_analyzed ?? "—"}
                      </span>
                    </span>
                    <span>
                      Signals:{" "}
                      <span className="text-foreground font-mono">
                        {profile.interaction_stats.total_signals ?? "—"}
                      </span>
                    </span>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="scores" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                Fit Scores (0–100)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {scores && Object.keys(scores).length > 0 ? (
                Object.entries(scores).map(([dim, data]) => (
                  <div key={dim} className="space-y-2">
                    <ScoreBar
                      label={dim.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      value={data.score}
                    />
                    {data.reasoning && (
                      <p className="text-xs text-muted-foreground pl-1">
                        {data.reasoning}
                      </p>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">
                  No scores computed yet. Run extraction and scoring first.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="adaptation" className="space-y-4">
          {adaptation ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">
                    Adaptation Rules
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {adaptation.adaptations.length > 0 ? (
                    <ul className="space-y-2">
                      {adaptation.adaptations.map((rule, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 text-sm text-muted-foreground"
                        >
                          <span className="mt-1 h-1 w-1 rounded-full bg-foreground/50 shrink-0" />
                          {rule}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      No specific adaptations. Using default behavior.
                    </p>
                  )}
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">
                    System Prompt Preview
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="whitespace-pre-wrap text-xs text-muted-foreground font-mono bg-secondary/50 rounded-lg p-4 max-h-96 overflow-auto">
                    {adaptation.system_prompt_preview}
                  </pre>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="py-8 text-center">
                <p className="text-xs text-muted-foreground">
                  Could not load adaptation preview. Profile may not have enough data.
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
