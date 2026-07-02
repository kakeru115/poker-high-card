-- Poker High Card for Next.js
-- Run this file once in the Supabase SQL Editor.
-- Also enable Anonymous Sign-Ins in Authentication > Providers.

create extension if not exists pgcrypto;

create table if not exists public.poker_rooms (
    id uuid primary key default gen_random_uuid(),
    code text not null unique check (char_length(code) = 6),
    capacity integer not null check (capacity between 2 and 10),
    status text not null default 'waiting'
        check (status in ('waiting', 'dealt')),
    locked boolean not null default false,
    host_user_id uuid not null,
    draw_id uuid,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.poker_room_members (
    id uuid primary key default gen_random_uuid(),
    room_id uuid not null references public.poker_rooms(id) on delete cascade,
    user_id uuid not null,
    name text not null check (char_length(name) between 1 and 24),
    ready boolean not null default false,
    seat_index integer not null,
    joined_at timestamptz not null default now(),
    unique (room_id, user_id),
    unique (room_id, seat_index)
);

create table if not exists public.poker_private_cards (
    room_id uuid not null references public.poker_rooms(id) on delete cascade,
    user_id uuid not null,
    rank text not null
        check (rank in ('2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A')),
    suit text not null
        check (suit in ('Clubs', 'Diamonds', 'Hearts', 'Spades')),
    primary key (room_id, user_id)
);

create index if not exists poker_room_members_room_idx
on public.poker_room_members (room_id, seat_index);

create index if not exists poker_rooms_updated_idx
on public.poker_rooms (updated_at);

alter table public.poker_rooms enable row level security;
alter table public.poker_room_members enable row level security;
alter table public.poker_private_cards enable row level security;

create or replace function public.is_poker_room_member(check_room_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.poker_room_members
        where room_id = check_room_id
          and user_id = auth.uid()
    );
$$;

revoke all on function public.is_poker_room_member(uuid) from public;
grant execute on function public.is_poker_room_member(uuid) to authenticated;

drop policy if exists "Players can see their room" on public.poker_rooms;
create policy "Players can see their room"
on public.poker_rooms for select
to authenticated
using (public.is_poker_room_member(id));

drop policy if exists "Players can see members at their table" on public.poker_room_members;
create policy "Players can see members at their table"
on public.poker_room_members for select
to authenticated
using (public.is_poker_room_member(room_id));

drop policy if exists "Players can only see their own card" on public.poker_private_cards;
create policy "Players can only see their own card"
on public.poker_private_cards for select
to authenticated
using (user_id = auth.uid());

revoke insert, update, delete on public.poker_rooms from anon, authenticated;
revoke insert, update, delete on public.poker_room_members from anon, authenticated;
revoke insert, update, delete on public.poker_private_cards from anon, authenticated;

grant select on public.poker_rooms to authenticated;
grant select on public.poker_room_members to authenticated;
grant select on public.poker_private_cards to authenticated;

create or replace function public.touch_poker_room()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists touch_poker_room_updated_at on public.poker_rooms;
create trigger touch_poker_room_updated_at
before update on public.poker_rooms
for each row execute function public.touch_poker_room();

create or replace function public.create_poker_room(
    player_name text,
    player_capacity integer
)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
    new_room public.poker_rooms;
    new_code text;
    alphabet constant text := '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
begin
    if auth.uid() is null then
        raise exception 'Authentication is required';
    end if;
    if char_length(trim(player_name)) not between 1 and 24 then
        raise exception 'Enter a player name';
    end if;
    if player_capacity not between 2 and 10 then
        raise exception 'Player count must be between 2 and 10';
    end if;

    loop
        select string_agg(
            substr(alphabet, 1 + floor(random() * length(alphabet))::integer, 1),
            ''
        )
        into new_code
        from generate_series(1, 6);

        begin
            insert into public.poker_rooms (
                code, capacity, host_user_id
            )
            values (
                new_code, player_capacity, auth.uid()
            )
            returning * into new_room;
            exit;
        exception when unique_violation then
            -- Generate another six-character code.
        end;
    end loop;

    insert into public.poker_room_members (
        room_id, user_id, name, ready, seat_index
    )
    values (
        new_room.id, auth.uid(), trim(player_name), false, 0
    );

    return jsonb_build_object(
        'room_id', new_room.id,
        'code', new_room.code
    );
end;
$$;

create or replace function public.join_poker_room(
    room_code text,
    player_name text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
    target_room public.poker_rooms;
    next_seat integer;
begin
    if auth.uid() is null then
        raise exception 'Authentication is required';
    end if;
    if char_length(trim(player_name)) not between 1 and 24 then
        raise exception 'Enter a player name';
    end if;

    select *
    into target_room
    from public.poker_rooms
    where code = upper(trim(room_code))
    for update;

    if target_room.id is null then
        raise exception 'Table not found';
    end if;

    if exists (
        select 1
        from public.poker_room_members
        where room_id = target_room.id and user_id = auth.uid()
    ) then
        update public.poker_room_members
        set name = trim(player_name)
        where room_id = target_room.id and user_id = auth.uid();
        return target_room.id;
    end if;

    if target_room.status <> 'waiting' then
        raise exception 'Cards have already been dealt';
    end if;
    if target_room.locked then
        raise exception 'The host has locked this table';
    end if;
    if (
        select count(*)
        from public.poker_room_members
        where room_id = target_room.id
    ) >= target_room.capacity then
        raise exception 'This table is full';
    end if;

    select coalesce(max(seat_index), -1) + 1
    into next_seat
    from public.poker_room_members
    where room_id = target_room.id;

    insert into public.poker_room_members (
        room_id, user_id, name, ready, seat_index
    )
    values (
        target_room.id, auth.uid(), trim(player_name), false, next_seat
    );

    return target_room.id;
end;
$$;

create or replace function public.set_poker_ready(
    target_room_id uuid,
    is_ready boolean
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.poker_room_members
    set ready = is_ready
    where room_id = target_room_id and user_id = auth.uid();

    if not found then
        raise exception 'You are not seated at this table';
    end if;
end;
$$;

create or replace function public.set_poker_room_lock(
    target_room_id uuid,
    is_locked boolean
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    update public.poker_rooms
    set locked = is_locked
    where id = target_room_id
      and host_user_id = auth.uid()
      and status = 'waiting';

    if not found then
        raise exception 'Only the host can lock this table';
    end if;
end;
$$;

create or replace function public.remove_poker_member(
    target_room_id uuid,
    target_user_id uuid
)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1 from public.poker_rooms
        where id = target_room_id and host_user_id = auth.uid()
    ) then
        raise exception 'Only the host can remove a player';
    end if;
    if target_user_id = auth.uid() then
        raise exception 'The host cannot remove themselves';
    end if;

    delete from public.poker_room_members
    where room_id = target_room_id and user_id = target_user_id;
end;
$$;

create or replace function public.deal_poker_room(target_room_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
    target_room public.poker_rooms;
    member_count integer;
    ready_count integer;
begin
    select *
    into target_room
    from public.poker_rooms
    where id = target_room_id
    for update;

    if target_room.host_user_id <> auth.uid() then
        raise exception 'Only the host can deal';
    end if;
    if target_room.status <> 'waiting' or not target_room.locked then
        raise exception 'Lock the room before dealing';
    end if;

    select count(*), count(*) filter (where ready)
    into member_count, ready_count
    from public.poker_room_members
    where room_id = target_room_id;

    if member_count < 2 or member_count <> ready_count then
        raise exception 'Every player must be ready';
    end if;

    delete from public.poker_private_cards
    where room_id = target_room_id;

    with shuffled_deck as (
        select
            rank,
            suit,
            row_number() over (order by random()) as card_number
        from unnest(array[
            '2', '3', '4', '5', '6', '7', '8', '9',
            '10', 'J', 'Q', 'K', 'A'
        ]::text[]) as rank_values(rank)
        cross join unnest(array[
            'Clubs', 'Diamonds', 'Hearts', 'Spades'
        ]::text[]) as suit_values(suit)
    ),
    seated_players as (
        select
            user_id,
            row_number() over (order by seat_index) as card_number
        from public.poker_room_members
        where room_id = target_room_id
    )
    insert into public.poker_private_cards (room_id, user_id, rank, suit)
    select target_room_id, seated_players.user_id, shuffled_deck.rank, shuffled_deck.suit
    from seated_players
    join shuffled_deck using (card_number);

    update public.poker_rooms
    set status = 'dealt', locked = true, draw_id = gen_random_uuid()
    where id = target_room_id;
end;
$$;

create or replace function public.reset_poker_room(target_room_id uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
    if not exists (
        select 1 from public.poker_rooms
        where id = target_room_id and host_user_id = auth.uid()
    ) then
        raise exception 'Only the host can start another round';
    end if;

    delete from public.poker_private_cards
    where room_id = target_room_id;

    update public.poker_room_members
    set ready = false
    where room_id = target_room_id;

    update public.poker_rooms
    set status = 'waiting', locked = false, draw_id = null
    where id = target_room_id;
end;
$$;

revoke all on function public.create_poker_room(text, integer) from public;
revoke all on function public.join_poker_room(text, text) from public;
revoke all on function public.set_poker_ready(uuid, boolean) from public;
revoke all on function public.set_poker_room_lock(uuid, boolean) from public;
revoke all on function public.remove_poker_member(uuid, uuid) from public;
revoke all on function public.deal_poker_room(uuid) from public;
revoke all on function public.reset_poker_room(uuid) from public;

grant execute on function public.create_poker_room(text, integer) to authenticated;
grant execute on function public.join_poker_room(text, text) to authenticated;
grant execute on function public.set_poker_ready(uuid, boolean) to authenticated;
grant execute on function public.set_poker_room_lock(uuid, boolean) to authenticated;
grant execute on function public.remove_poker_member(uuid, uuid) to authenticated;
grant execute on function public.deal_poker_room(uuid) to authenticated;
grant execute on function public.reset_poker_room(uuid) to authenticated;

do $$
begin
    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'poker_rooms'
    ) then
        alter publication supabase_realtime add table public.poker_rooms;
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'poker_room_members'
    ) then
        alter publication supabase_realtime add table public.poker_room_members;
    end if;

    if not exists (
        select 1
        from pg_publication_tables
        where pubname = 'supabase_realtime'
          and schemaname = 'public'
          and tablename = 'poker_private_cards'
    ) then
        alter publication supabase_realtime add table public.poker_private_cards;
    end if;
end
$$;
