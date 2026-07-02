-- Run this once in the Supabase SQL Editor.
-- The app uses the service-role key from Streamlit secrets, so public clients
-- cannot read or change table data directly.

create table if not exists public.poker_tables (
    code text primary key check (char_length(code) = 6),
    table_data jsonb not null,
    updated_at timestamptz not null default now()
);

alter table public.poker_tables enable row level security;
revoke all on table public.poker_tables from anon, authenticated;

create or replace function public.set_poker_table_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists poker_tables_updated_at on public.poker_tables;
create trigger poker_tables_updated_at
before update on public.poker_tables
for each row
execute function public.set_poker_table_updated_at();

create index if not exists poker_tables_updated_at_idx
on public.poker_tables (updated_at);
