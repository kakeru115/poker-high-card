# Poker High Card Web

This directory contains the Next.js version of Poker High Card. The existing
Streamlit app remains available from the repository root while the migration is
tested.

## Included

- Japanese and English interfaces
- Remembered nickname
- Private device, table draw, and auto judge modes
- A complete 52-card deck with no duplicate draws
- Rank and suit comparison
- Circular dealer seat map
- Responsive mobile layout
- Optional sound and reduced-motion controls
- Supabase anonymous authentication, Realtime lobby updates, and private cards
  protected by Row Level Security

## Run locally

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:3000>.

Auto judge and table draw work without Supabase. Private device mode needs the
setup below.

## Supabase setup

1. Create a Supabase project.
2. Open **Authentication > Providers > Anonymous Sign-Ins** and enable it.
3. Run `supabase/schema.sql` in the Supabase SQL Editor.
4. Copy `.env.local.example` to `.env.local`.
5. Add the project URL and publishable/anon key.
6. Restart the Next.js development server.

The browser uses an anonymous Supabase account for each device. Lobby members
are shared in Realtime, while Row Level Security only allows a player to read
their own dealt card.

## Deploy

Deploy the repository to Vercel and select `web` as the project Root Directory.
Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in the Vercel
project environment variables.
