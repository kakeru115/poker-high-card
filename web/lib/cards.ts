export const ranks = [
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "J",
  "Q",
  "K",
  "A",
] as const;

export const suits = ["Clubs", "Diamonds", "Hearts", "Spades"] as const;

export type Rank = (typeof ranks)[number];
export type Suit = (typeof suits)[number];
export type Card = { rank: Rank; suit: Suit };
export type DrawResult = { id: string; player: string; card: Card };

const rankFiles: Partial<Record<Rank, string>> = {
  A: "ace",
  J: "jack",
  Q: "queen",
  K: "king",
};

export function createDeck(): Card[] {
  return suits.flatMap((suit) => ranks.map((rank) => ({ rank, suit })));
}

export function shuffle<T>(items: T[]): T[] {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [result[index], result[swapIndex]] = [result[swapIndex], result[index]];
  }
  return result;
}

export function drawCards(players: string[]): DrawResult[] {
  const deck = shuffle(createDeck());
  return players.map((player, index) => ({
    id: `${Date.now()}-${index}`,
    player,
    card: deck[index],
  }));
}

export function cardStrength(card: Card): number {
  return ranks.indexOf(card.rank) * suits.length + suits.indexOf(card.suit);
}

export function sortedResults(results: DrawResult[]): DrawResult[] {
  return [...results].sort(
    (left, right) => cardStrength(right.card) - cardStrength(left.card),
  );
}

export function cardImage(card: Card): string {
  const rank = rankFiles[card.rank] ?? card.rank;
  const suffix = ["J", "Q", "K"].includes(card.rank) ? "2" : "";
  return `/cards/${rank}_of_${card.suit.toLowerCase()}${suffix}.svg`;
}

export function suitSymbol(suit: Suit): string {
  return { Clubs: "♣", Diamonds: "♦", Hearts: "♥", Spades: "♠" }[suit];
}
