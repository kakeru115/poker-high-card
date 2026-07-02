# Poker High Card

Poker High Card is a small Streamlit app that helps a poker table decide the first dealer or button position. Each player draws one card, and the strongest card wins.

Live app: https://poker-high-card.streamlit.app/

![Poker High Card title screen](assets/poker-title.png)

## Next.js Migration

A new Next.js + Supabase version is being developed in [`web/`](web/README.md).
The existing Streamlit app remains available while the new version is tested.
The web version adds a more flexible responsive interface, smooth client-side
transitions, Supabase Realtime lobby updates, anonymous device identities, and
Row Level Security so each private card can only be read by its owner.

## Features

- Choose 2 to 10 players.
- Enter custom player names.
- Build a standard 52-card deck.
- Draw one unique card per player.
- Choose a play style directly from the title screen.
- Save your nickname automatically when a play style is selected.
- Restore the same private-table seat after a browser reload.
- Switch between Japanese and English, with Japanese shown first.
- Choose Private device mode so each person can join from their own browser and see only their own card.
- Join a private table by scanning its QR code.
- Use a dedicated host lobby with Ready states, room locking, and player removal.
- Keep private tables available across app restarts with Supabase.
- Use table codes without ambiguous `0/O` or `1/I` characters.
- Remove inactive private tables automatically after 24 hours.
- Retry a table connection without leaving the current screen.
- Choose Table mode to show cards only and let everyone judge together.
- Choose Auto judge mode to show the winner and ranking automatically.
- Hear original music for the title screen, gameplay, and result reveal.
- Keep music off by default and let visitors turn it on at any time.
- Compare cards by poker high-card rules.
- Break rank ties by suit.
- Show every player's card with a consistent illustrated English-pattern deck.
- Animate cards as they are dealt.
- Reduce animations manually or through the device accessibility preference.
- Highlight the winner.
- Show a circular seat map with the first dealer marked.
- Celebrate your first-place draw with a large message, balloons, and result fanfare.
- Show a ranked results table with comparison details.
- Warn when multiple players have the same name.
- Play another round with the same players.

## Card Strength

Ranks are compared in this order:

`A > K > Q > J > 10 > 9 > 8 > 7 > 6 > 5 > 4 > 3 > 2`

If two players draw the same rank, suits are compared in this order:

`Spades > Hearts > Diamonds > Clubs`

## Tech Stack

- Python
- Streamlit
- Supabase
- Browser Local Storage

## Card Artwork

The card faces in `assets/cards` come from the
[Webisso open-source playing cards](https://github.com/webisso/playing-cards)
project and are used under the MIT License. A copy of the license is included
at `assets/cards/LICENSE.webisso`.

## How to Run

Install the dependency:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app.py
```

Then open the local URL shown in your terminal.

For Private device mode, have each player open the app from their own device or browser session. The host creates a table, then shares its QR code. The QR URL contains only the table code, so every player still joins with their own name and receives a separate private identity. Players can press Refresh table while waiting. When the table is full, the host presses Deal cards to start.

## Supabase Setup

1. Create a Supabase project.
2. Run `supabase_schema.sql` in the Supabase SQL Editor.
3. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
4. Add the project URL and service-role key.

Streamlit Community Cloud uses the same two values in the app's **Secrets**
settings. The service-role key must never be committed to GitHub.

When Supabase secrets are not present, local development falls back to
`private_tables.json`.

## LinkedIn

The sidebar includes a **Share on LinkedIn** button for the live app. A
ready-to-use Japanese post is available in `LINKEDIN_POST.md`. The title artwork
at `assets/poker-title.png` can be attached as the post image.

## GitHub

This project is ready to publish to GitHub. It includes:

- `.gitignore` to keep Python cache files, virtual environments, local secrets, and macOS metadata out of the repository.
- GitHub Actions workflow at `.github/workflows/python-check.yml`.

The workflow installs dependencies and checks that `app.py` has valid Python syntax whenever code is pushed or a pull request is opened.
