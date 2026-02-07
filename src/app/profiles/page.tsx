import { createClient } from "@/lib/supabase/server";
import { ProfileList } from "@/components/profile-list";

export default async function ProfilesPage() {
  const supabase = await createClient();

  const { data: profiles, count } = await supabase
    .from("user_profiles")
    .select("*, behavioral_scores(*)", { count: "exact" })
    .order("total_conversations", { ascending: false })
    .limit(50);

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-foreground text-balance">
          User Profiles
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {count?.toLocaleString() ?? 0} unique users tracked
        </p>
      </div>

      {profiles && profiles.length > 0 ? (
        <ProfileList initialProfiles={profiles} totalCount={count ?? 0} />
      ) : (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border p-12 text-center">
          <svg
            className="h-12 w-12 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
            />
          </svg>
          <h2 className="mt-4 text-lg font-medium text-foreground">
            No profiles yet
          </h2>
          <p className="mt-2 max-w-sm text-sm text-muted-foreground">
            Ingest conversation data to generate user profiles and behavioral
            scores.
          </p>
        </div>
      )}
    </div>
  );
}
