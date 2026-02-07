-- Gail: Adaptive Behavioral Profiling Agent System
-- Core schema for conversation storage, user profiles, and behavioral scoring

-- Conversations table
create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  conversation_id text not null unique,
  user_id text not null,
  model text,
  language text,
  turn_count integer default 0,
  message_count integer default 0,
  created_at timestamptz default now()
);

create index if not exists idx_conversations_user_id on public.conversations(user_id);
create index if not exists idx_conversations_language on public.conversations(language);

-- Messages table
create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id text not null references public.conversations(conversation_id) on delete cascade,
  user_id text not null,
  role text not null,
  content text not null,
  message_index integer not null,
  conversation_turn integer,
  redacted boolean default false,
  created_at timestamptz default now()
);

create index if not exists idx_messages_conversation_id on public.messages(conversation_id);
create index if not exists idx_messages_user_id on public.messages(user_id);

-- User profiles (aggregated behavioral data)
create table if not exists public.user_profiles (
  user_id text primary key,
  total_conversations integer default 0,
  total_messages integer default 0,
  languages text[] default '{}',
  models_used text[] default '{}',
  avg_turns_per_conversation numeric(5,2) default 0,
  avg_messages_per_conversation numeric(5,2) default 0,
  first_seen timestamptz,
  last_seen timestamptz,
  profile_generated boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Behavioral dimension scores (1-10 scale)
create table if not exists public.behavioral_scores (
  id uuid primary key default gen_random_uuid(),
  user_id text not null references public.user_profiles(user_id) on delete cascade,
  dimension text not null,
  score numeric(3,1) not null check (score >= 1 and score <= 10),
  confidence numeric(3,2) not null check (confidence >= 0 and confidence <= 1),
  evidence_summary text,
  updated_at timestamptz default now(),
  unique(user_id, dimension)
);

create index if not exists idx_behavioral_scores_user_id on public.behavioral_scores(user_id);
create index if not exists idx_behavioral_scores_dimension on public.behavioral_scores(dimension);

-- Ingestion job tracking
create table if not exists public.ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  status text not null default 'pending' check (status in ('pending', 'processing', 'completed', 'failed')),
  total_records integer default 0,
  processed_records integer default 0,
  error_message text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Disable RLS for this internal research tool (no public user auth needed)
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.user_profiles enable row level security;
alter table public.behavioral_scores enable row level security;
alter table public.ingestion_jobs enable row level security;

-- Allow all access via service role (internal tool)
create policy "allow_all_conversations" on public.conversations for all using (true) with check (true);
create policy "allow_all_messages" on public.messages for all using (true) with check (true);
create policy "allow_all_user_profiles" on public.user_profiles for all using (true) with check (true);
create policy "allow_all_behavioral_scores" on public.behavioral_scores for all using (true) with check (true);
create policy "allow_all_ingestion_jobs" on public.ingestion_jobs for all using (true) with check (true);
