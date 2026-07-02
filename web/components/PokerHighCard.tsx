"use client";

import {
  ArrowLeft,
  Check,
  Copy,
  Crown,
  Eye,
  EyeOff,
  Globe2,
  Lock,
  LockOpen,
  Music,
  Music2,
  Play,
  RefreshCw,
  RotateCcw,
  Sparkles,
  Trash2,
  UserRound,
  UsersRound,
  VolumeX,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import {
  Card,
  DrawResult,
  cardImage,
  drawCards,
  sortedResults,
  suitSymbol,
} from "@/lib/cards";
import { getSupabase, hasSupabaseConfig } from "@/lib/supabase";

type Language = "ja" | "en";
type Mode = "private" | "table" | "judge";
type Screen = "title" | "game";

type PokerRoom = {
  id: string;
  code: string;
  capacity: number;
  status: "waiting" | "dealt";
  locked: boolean;
  host_user_id: string;
  draw_id: string | null;
};

type RoomMember = {
  id: string;
  room_id: string;
  user_id: string;
  name: string;
  ready: boolean;
  seat_index: number;
};

type PrivateCard = {
  rank: Card["rank"];
  suit: Card["suit"];
};

const modeOptions: Array<{
  id: Mode;
  icon: typeof Eye;
  ja: string;
  en: string;
  detailJa: string;
  detailEn: string;
}> = [
  {
    id: "private",
    icon: EyeOff,
    ja: "各自の端末",
    en: "Private device",
    detailJa: "自分のカードだけを見る",
    detailEn: "Only see your own card",
  },
  {
    id: "table",
    icon: UsersRound,
    ja: "みんなで判定",
    en: "Table draw",
    detailJa: "全員で見せ合って決める",
    detailEn: "Compare cards together",
  },
  {
    id: "judge",
    icon: Crown,
    ja: "自動判定",
    en: "Auto judge",
    detailJa: "順位まで自動で表示",
    detailEn: "Show the full ranking",
  },
];

const nicknameStorageKey = "poker-high-card-nickname";
const nicknameChangeEvent = "poker-high-card-nickname-change";

function subscribeToNickname(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(nicknameChangeEvent, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(nicknameChangeEvent, onStoreChange);
  };
}

function getNicknameSnapshot() {
  return localStorage.getItem(nicknameStorageKey) ?? "";
}

function useRememberedNickname() {
  const nickname = useSyncExternalStore(
    subscribeToNickname,
    getNicknameSnapshot,
    () => "",
  );

  const remember = useCallback((value: string) => {
    localStorage.setItem(nicknameStorageKey, value);
    window.dispatchEvent(new Event(nicknameChangeEvent));
  }, []);

  return { nickname, remember };
}

function playTone(notes: number[], volume = 0.1) {
  if (typeof window === "undefined") return;
  const AudioContextClass =
    window.AudioContext ??
    (
      window as typeof window & {
        webkitAudioContext?: typeof AudioContext;
      }
    ).webkitAudioContext;
  if (!AudioContextClass) return;

  const context = new AudioContextClass();
  notes.forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = frequency;
    oscillator.type = "triangle";
    gain.gain.setValueAtTime(0.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(
      volume,
      context.currentTime + index * 0.11 + 0.01,
    );
    gain.gain.exponentialRampToValueAtTime(
      0.0001,
      context.currentTime + index * 0.11 + 0.22,
    );
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(context.currentTime + index * 0.11);
    oscillator.stop(context.currentTime + index * 0.11 + 0.24);
  });
  window.setTimeout(() => void context.close(), notes.length * 110 + 350);
}

function useAmbientMusic(enabled: boolean, screen: Screen) {
  useEffect(() => {
    if (!enabled) return;

    const titleNotes = [261, 329, 392, 329];
    const gameNotes = [220, 293, 349, 293];
    const playPhrase = () =>
      playTone(screen === "title" ? titleNotes : gameNotes, 0.035);

    playPhrase();
    const interval = window.setInterval(playPhrase, 5200);
    return () => window.clearInterval(interval);
  }, [enabled, screen]);
}

export function PokerHighCard() {
  const { nickname, remember } = useRememberedNickname();
  const [language, setLanguage] = useState<Language>("ja");
  const [screen, setScreen] = useState<Screen>("title");
  const [mode, setMode] = useState<Mode>("judge");
  const [musicEnabled, setMusicEnabled] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  useAmbientMusic(musicEnabled, screen);

  useEffect(() => {
    const tableCode = new URLSearchParams(window.location.search).get("table");
    queueMicrotask(() => {
      setReducedMotion(
        window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      );
      if (tableCode) {
        setMode("private");
        setScreen("game");
      }
    });
  }, []);

  const t = useCallback(
    (ja: string, en: string) => (language === "ja" ? ja : en),
    [language],
  );

  const chooseMode = (selectedMode: Mode) => {
    if (!nickname.trim()) return;
    remember(nickname.trim());
    setMode(selectedMode);
    setScreen("game");
  };

  return (
    <main className="app-shell">
      {screen === "title" ? (
        <TitleScreen
          language={language}
          setLanguage={setLanguage}
          nickname={nickname}
          remember={remember}
          chooseMode={chooseMode}
          musicEnabled={musicEnabled}
          setMusicEnabled={setMusicEnabled}
          reducedMotion={reducedMotion}
          setReducedMotion={setReducedMotion}
          t={t}
        />
      ) : (
        <GameScreen
          language={language}
          setLanguage={setLanguage}
          nickname={nickname}
          remember={remember}
          mode={mode}
          setMode={setMode}
          musicEnabled={musicEnabled}
          setMusicEnabled={setMusicEnabled}
          reducedMotion={reducedMotion}
          setReducedMotion={setReducedMotion}
          goHome={() => setScreen("title")}
          t={t}
        />
      )}
    </main>
  );
}

type SharedProps = {
  language: Language;
  setLanguage: (language: Language) => void;
  musicEnabled: boolean;
  setMusicEnabled: (enabled: boolean) => void;
  reducedMotion: boolean;
  setReducedMotion: (enabled: boolean) => void;
  t: (ja: string, en: string) => string;
};

function TitleScreen({
  language,
  setLanguage,
  nickname,
  remember,
  chooseMode,
  musicEnabled,
  setMusicEnabled,
  reducedMotion,
  setReducedMotion,
  t,
}: SharedProps & {
  nickname: string;
  remember: (nickname: string) => void;
  chooseMode: (mode: Mode) => void;
}) {
  return (
    <section className="title-screen">
      <div className="title-image" aria-hidden="true" />
      <div className="title-shade" aria-hidden="true" />
      <header className="title-toolbar">
        <LanguageControl language={language} setLanguage={setLanguage} />
        <IconToggle
          active={musicEnabled}
          label={t("音楽", "Music")}
          onClick={() => setMusicEnabled(!musicEnabled)}
          activeIcon={Music2}
          inactiveIcon={VolumeX}
        />
      </header>

      <div className="title-content">
        <p className="title-kicker">DEAL THE FIRST CARD</p>
        <h1>Poker High Card</h1>
        <p className="title-lead">
          {t(
            "一枚のカードで、最初のディーラーを決めよう。",
            "One card decides who deals first.",
          )}
        </p>

        <label className="nickname-field">
          <span>{t("ニックネーム", "Nickname")}</span>
          <input
            value={nickname}
            maxLength={24}
            onChange={(event) => remember(event.target.value)}
            placeholder={t("名前を入力", "Enter your name")}
          />
        </label>

        <div className="mode-grid" aria-label={t("遊び方", "Play style")}>
          {modeOptions.map((option) => {
            const Icon = option.icon;
            return (
              <button
                className="mode-choice"
                disabled={!nickname.trim()}
                key={option.id}
                onClick={() => chooseMode(option.id)}
              >
                <Icon size={24} aria-hidden="true" />
                <strong>{language === "ja" ? option.ja : option.en}</strong>
                <span>
                  {language === "ja" ? option.detailJa : option.detailEn}
                </span>
              </button>
            );
          })}
        </div>

        <label className="motion-control">
          <input
            type="checkbox"
            checked={reducedMotion}
            onChange={(event) => setReducedMotion(event.target.checked)}
          />
          <span>{t("アニメーションを減らす", "Reduce motion")}</span>
        </label>
      </div>
    </section>
  );
}

function GameScreen({
  language,
  setLanguage,
  nickname,
  remember,
  mode,
  setMode,
  musicEnabled,
  setMusicEnabled,
  reducedMotion,
  setReducedMotion,
  goHome,
  t,
}: SharedProps & {
  nickname: string;
  remember: (nickname: string) => void;
  mode: Mode;
  setMode: (mode: Mode) => void;
  goHome: () => void;
}) {
  return (
    <div className="game-layout">
      <header className="game-header">
        <button className="icon-button" onClick={goHome} title={t("戻る", "Back")}>
          <ArrowLeft aria-hidden="true" />
        </button>
        <button className="wordmark" onClick={goHome}>
          Poker High Card
        </button>
        <div className="header-actions">
          <LanguageControl language={language} setLanguage={setLanguage} compact />
          <IconToggle
            active={musicEnabled}
            label={t("音楽", "Music")}
            onClick={() => setMusicEnabled(!musicEnabled)}
            activeIcon={Music}
            inactiveIcon={VolumeX}
          />
        </div>
      </header>

      <nav className="mode-tabs" aria-label={t("遊び方", "Play style")}>
        {modeOptions.map((option) => {
          const Icon = option.icon;
          return (
            <button
              className={mode === option.id ? "active" : ""}
              key={option.id}
              onClick={() => setMode(option.id)}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{language === "ja" ? option.ja : option.en}</span>
            </button>
          );
        })}
      </nav>

      <div className="game-content">
        {mode === "private" ? (
          <PrivateDeviceMode
            nickname={nickname}
            remember={remember}
            reducedMotion={reducedMotion}
            musicEnabled={musicEnabled}
            t={t}
          />
        ) : (
          <SharedDrawMode
            nickname={nickname}
            remember={remember}
            mode={mode}
            reducedMotion={reducedMotion}
            musicEnabled={musicEnabled}
            t={t}
          />
        )}
      </div>

      <footer className="game-footer">
        <p>
          {t(
            "Aが最強。同じ数字なら ♠ > ♥ > ♦ > ♣",
            "Ace is high. Ties: ♠ > ♥ > ♦ > ♣",
          )}
        </p>
        <label className="motion-control dark">
          <input
            type="checkbox"
            checked={reducedMotion}
            onChange={(event) => setReducedMotion(event.target.checked)}
          />
          <span>{t("動きを減らす", "Reduce motion")}</span>
        </label>
      </footer>
    </div>
  );
}

function SharedDrawMode({
  nickname,
  remember,
  mode,
  reducedMotion,
  musicEnabled,
  t,
}: {
  nickname: string;
  remember: (nickname: string) => void;
  mode: "table" | "judge";
  reducedMotion: boolean;
  musicEnabled: boolean;
  t: (ja: string, en: string) => string;
}) {
  const [playerCount, setPlayerCount] = useState(4);
  const [players, setPlayers] = useState(() => [
    nickname || "Player 1",
    "Player 2",
    "Player 3",
    "Player 4",
  ]);
  const [results, setResults] = useState<DrawResult[]>([]);

  useEffect(() => {
    queueMicrotask(() => {
      setPlayers((current) => {
        const next = Array.from(
          { length: playerCount },
          (_, index) => current[index] ?? `Player ${index + 1}`,
        );
        if (nickname && !results.length) next[0] = nickname;
        return next;
      });
    });
  }, [nickname, playerCount, results.length]);

  const ranking = useMemo(() => sortedResults(results), [results]);
  const winner = ranking[0];

  const draw = () => {
    const cleanPlayers = players.map(
      (name, index) => name.trim() || `Player ${index + 1}`,
    );
    remember(cleanPlayers[0]);
    setResults(drawCards(cleanPlayers));
    if (musicEnabled) {
      window.setTimeout(
        () => playTone([523, 659, 784, 1047], 0.12),
        180,
      );
    }
  };

  if (results.length) {
    return (
      <section className="result-view">
        {mode === "judge" && winner ? (
          <div className="winner-callout" aria-live="polite">
            <Crown aria-hidden="true" />
            <span>{t("最初のディーラー", "FIRST DEALER")}</span>
            <h2>
              {winner.player}
              {t("が一位だよ", " wins")}
            </h2>
          </div>
        ) : (
          <div className="section-heading">
            <p>{t("カードを見せ合おう", "SHOW YOUR CARDS")}</p>
            <h2>{t("勝者はみんなで判定", "Decide the winner together")}</h2>
          </div>
        )}

        {mode === "judge" && winner ? (
          <SeatMap results={results} winnerId={winner.id} t={t} />
        ) : null}

        <div className="cards-grid">
          {results.map((result, index) => (
            <PlayingCard
              key={result.id}
              result={result}
              winner={mode === "judge" && result.id === winner?.id}
              delay={reducedMotion ? 0 : index * 90}
              reducedMotion={reducedMotion}
            />
          ))}
        </div>

        {mode === "judge" ? (
          <ol className="ranking-list">
            {ranking.map((result, index) => (
              <li key={result.id}>
                <span className="rank-number">{index + 1}</span>
                <strong>{result.player}</strong>
                <span className="rank-card">
                  {result.card.rank} {suitSymbol(result.card.suit)}
                </span>
              </li>
            ))}
          </ol>
        ) : null}

        <button className="primary-button" onClick={() => setResults([])}>
          <RotateCcw size={18} aria-hidden="true" />
          {t("同じメンバーでもう一度", "Play again")}
        </button>
      </section>
    );
  }

  return (
    <section className="setup-view">
      <div className="section-heading">
        <p>{mode === "judge" ? "AUTO JUDGE" : "TABLE DRAW"}</p>
        <h1>
          {mode === "judge"
            ? t("最初のディーラーを決める", "Choose the first dealer")
            : t("一枚ずつ引いて見せ合う", "Draw and compare together")}
        </h1>
      </div>

      <div className="count-row">
        <label htmlFor="player-count">{t("プレイヤー数", "Players")}</label>
        <output>{playerCount}</output>
      </div>
      <input
        id="player-count"
        className="player-slider"
        type="range"
        min={2}
        max={10}
        value={playerCount}
        onChange={(event) => setPlayerCount(Number(event.target.value))}
      />

      <div className="player-inputs">
        {players.map((player, index) => (
          <label key={index}>
            <span>
              <UserRound size={16} aria-hidden="true" />
              {t(`プレイヤー ${index + 1}`, `Player ${index + 1}`)}
            </span>
            <input
              value={player}
              maxLength={24}
              onChange={(event) =>
                setPlayers((current) =>
                  current.map((name, playerIndex) =>
                    playerIndex === index ? event.target.value : name,
                  ),
                )
              }
            />
          </label>
        ))}
      </div>

      <button className="primary-button deal-button" onClick={draw}>
        <Sparkles size={20} aria-hidden="true" />
        {t("カードを配る", "Deal cards")}
      </button>
    </section>
  );
}

function SeatMap({
  results,
  winnerId,
  t,
}: {
  results: DrawResult[];
  winnerId: string;
  t: (ja: string, en: string) => string;
}) {
  return (
    <div className="seat-map" aria-label={t("席順", "Seat map")}>
      <div className="felt">
        <span>{t("最初のディーラー", "FIRST DEALER")}</span>
      </div>
      {results.map((result, index) => {
        const angle = (Math.PI * 2 * index) / results.length - Math.PI / 2;
        const left = 50 + Math.cos(angle) * 43;
        const top = 50 + Math.sin(angle) * 43;
        const winner = result.id === winnerId;
        return (
          <div
            className={`seat ${winner ? "dealer-seat" : ""}`}
            key={result.id}
            style={{ left: `${left}%`, top: `${top}%` }}
          >
            {winner ? <small>{t("ディーラー", "DEALER")}</small> : null}
            <span>{result.player}</span>
          </div>
        );
      })}
    </div>
  );
}

function PlayingCard({
  result,
  winner,
  delay,
  reducedMotion,
}: {
  result: DrawResult;
  winner: boolean;
  delay: number;
  reducedMotion: boolean;
}) {
  return (
    <article
      className={`card-result ${winner ? "winning-card" : ""} ${
        reducedMotion ? "no-motion" : ""
      }`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="card-name">
        {winner ? <Crown size={17} aria-hidden="true" /> : null}
        <strong>{result.player}</strong>
      </div>
      {/* The SVG files are bundled with the project and cover all 52 cards. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={cardImage(result.card)}
        alt={`${result.card.rank} of ${result.card.suit}`}
      />
    </article>
  );
}

function PrivateDeviceMode({
  nickname,
  remember,
  reducedMotion,
  musicEnabled,
  t,
}: {
  nickname: string;
  remember: (nickname: string) => void;
  reducedMotion: boolean;
  musicEnabled: boolean;
  t: (ja: string, en: string) => string;
}) {
  const configured = hasSupabaseConfig();
  const [room, setRoom] = useState<PokerRoom | null>(null);
  const [members, setMembers] = useState<RoomMember[]>([]);
  const [myCard, setMyCard] = useState<PrivateCard | null>(null);
  const [userId, setUserId] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [capacity, setCapacity] = useState(6);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lastDrawId = useRef<string | null>(null);

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("table");
    if (code) queueMicrotask(() => setJoinCode(code.toUpperCase()));
  }, []);

  const ensureAuth = useCallback(async () => {
    const supabase = getSupabase();
    if (!supabase) throw new Error("Supabase is not configured.");
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.user) {
      setUserId(session.user.id);
      return session.user;
    }
    const { data, error: authError } = await supabase.auth.signInAnonymously();
    if (authError || !data.user) throw authError ?? new Error("Sign in failed.");
    setUserId(data.user.id);
    return data.user;
  }, []);

  const loadRoom = useCallback(async (code: string) => {
    const supabase = getSupabase();
    if (!supabase) return;

    const { data: roomData, error: roomError } = await supabase
      .from("poker_rooms")
      .select("*")
      .eq("code", code)
      .single();
    if (roomError) throw roomError;

    const [{ data: memberData }, { data: cardData }] = await Promise.all([
      supabase
        .from("poker_room_members")
        .select("*")
        .eq("room_id", roomData.id)
        .order("seat_index"),
      supabase
        .from("poker_private_cards")
        .select("rank,suit")
        .eq("room_id", roomData.id)
        .maybeSingle(),
    ]);

    setRoom(roomData as PokerRoom);
    setMembers((memberData ?? []) as RoomMember[]);
    setMyCard((cardData as PrivateCard | null) ?? null);

    if (
      roomData.status === "dealt" &&
      roomData.draw_id &&
      lastDrawId.current !== roomData.draw_id
    ) {
      lastDrawId.current = roomData.draw_id;
      if (musicEnabled) playTone([392, 523, 659, 784], 0.12);
    }
  }, [musicEnabled]);

  useEffect(() => {
    if (!configured) return;
    const code = new URLSearchParams(window.location.search)
      .get("table")
      ?.toUpperCase();
    if (!code) return;

    let active = true;
    void (async () => {
      try {
        const supabase = getSupabase();
        const user = await ensureAuth();
        if (!supabase || !active) return;

        const { data: roomData } = await supabase
          .from("poker_rooms")
          .select("id,code")
          .eq("code", code)
          .maybeSingle();
        if (!roomData || !active) return;

        const { data: membership } = await supabase
          .from("poker_room_members")
          .select("id")
          .eq("room_id", roomData.id)
          .eq("user_id", user.id)
          .maybeSingle();
        if (membership && active) await loadRoom(code);
      } catch {
        // New visitors stay on the join screen and can retry explicitly.
      }
    })();

    return () => {
      active = false;
    };
  }, [configured, ensureAuth, loadRoom]);

  useEffect(() => {
    if (!configured || !room?.id) return;
    const supabase = getSupabase();
    if (!supabase) return;

    const refresh = () => void loadRoom(room.code);
    const channel = supabase
      .channel(`poker-room-${room.id}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "poker_rooms",
          filter: `id=eq.${room.id}`,
        },
        refresh,
      )
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "poker_room_members",
          filter: `room_id=eq.${room.id}`,
        },
        refresh,
      )
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "poker_private_cards",
          filter: `room_id=eq.${room.id}`,
        },
        refresh,
      )
      .subscribe();

    return () => {
      void supabase.removeChannel(channel);
    };
  }, [configured, loadRoom, room?.code, room?.id]);

  const runAction = async (action: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (actionError) {
      setError(
        actionError instanceof Error
          ? actionError.message
          : t("接続に失敗しました。", "Connection failed."),
      );
    } finally {
      setBusy(false);
    }
  };

  const createRoom = () =>
    runAction(async () => {
      const supabase = getSupabase();
      const user = await ensureAuth();
      if (!supabase) return;
      remember(nickname.trim());
      const { data, error: rpcError } = await supabase.rpc(
        "create_poker_room",
        {
          player_name: nickname.trim(),
          player_capacity: capacity,
        },
      );
      if (rpcError) throw rpcError;
      const created = data as { code: string; room_id: string };
      setUserId(user.id);
      window.history.replaceState(null, "", `?table=${created.code}`);
      await loadRoom(created.code);
    });

  const joinRoom = () =>
    runAction(async () => {
      const supabase = getSupabase();
      const user = await ensureAuth();
      if (!supabase) return;
      remember(nickname.trim());
      const code = joinCode.trim().toUpperCase();
      const { error: rpcError } = await supabase.rpc("join_poker_room", {
        room_code: code,
        player_name: nickname.trim(),
      });
      if (rpcError) throw rpcError;
      setUserId(user.id);
      window.history.replaceState(null, "", `?table=${code}`);
      await loadRoom(code);
    });

  const rpc = (name: string, params: Record<string, unknown>) =>
    runAction(async () => {
      const supabase = getSupabase();
      if (!supabase || !room) return;
      const { error: rpcError } = await supabase.rpc(name, params);
      if (rpcError) throw rpcError;
      await loadRoom(room.code);
    });

  if (!configured) {
    return (
      <section className="private-intro">
        <div className="section-heading">
          <p>PRIVATE DEVICE</p>
          <h1>{t("自分のカードは自分だけに", "Your card stays private")}</h1>
        </div>
        <div className="configuration-panel">
          <Lock size={28} aria-hidden="true" />
          <div>
            <h2>{t("Supabase接続待ち", "Connect Supabase")}</h2>
            <p>
              {t(
                "設定後は、QRやコードで同じ部屋に入り、画面を更新せずリアルタイムでReadyと配札が同期します。",
                "After setup, players join by code and Ready states and cards update live without refreshing.",
              )}
            </p>
          </div>
        </div>
      </section>
    );
  }

  if (!room) {
    return (
      <section className="private-intro">
        <div className="section-heading">
          <p>PRIVATE DEVICE</p>
          <h1>{t("同じテーブルに集まる", "Meet at one table")}</h1>
        </div>
        <div className="private-entry">
          <div>
            <h2>{t("テーブルを作る", "Create table")}</h2>
            <label>
              {t("参加人数", "Players")}
              <select
                value={capacity}
                onChange={(event) => setCapacity(Number(event.target.value))}
              >
                {Array.from({ length: 9 }, (_, index) => index + 2).map(
                  (value) => (
                    <option key={value}>{value}</option>
                  ),
                )}
              </select>
            </label>
            <button
              className="primary-button"
              disabled={busy || !nickname.trim()}
              onClick={createRoom}
            >
              <Play size={18} aria-hidden="true" />
              {t("ホストとして作成", "Create as host")}
            </button>
          </div>
          <div>
            <h2>{t("テーブルに入る", "Join table")}</h2>
            <label>
              {t("6文字のコード", "6-character code")}
              <input
                className="code-input"
                value={joinCode}
                maxLength={6}
                onChange={(event) =>
                  setJoinCode(event.target.value.toUpperCase())
                }
              />
            </label>
            <button
              className="secondary-button"
              disabled={busy || !nickname.trim() || joinCode.length !== 6}
              onClick={joinRoom}
            >
              {t("参加する", "Join")}
            </button>
          </div>
        </div>
        {error ? <p className="error-message">{error}</p> : null}
      </section>
    );
  }

  const me = members.find((member) => member.user_id === userId);
  const isHost = room.host_user_id === userId;
  const allReady = members.length >= 2 && members.every((member) => member.ready);
  const shareUrl =
    typeof window === "undefined"
      ? ""
      : `${window.location.origin}?table=${room.code}`;

  if (room.status === "dealt") {
    return (
      <section className="private-result">
        <p className="room-code-label">{t("テーブル", "TABLE")} {room.code}</p>
        {myCard ? (
          <>
            <p>{t("あなたのカード", "YOUR CARD")}</p>
            <div className={`private-card ${reducedMotion ? "no-motion" : ""}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={cardImage(myCard)} alt={`${myCard.rank} of ${myCard.suit}`} />
            </div>
            <h2>
              {myCard.rank} {suitSymbol(myCard.suit)}
            </h2>
            <p className="private-prompt">
              {t(
                "周りの人と見せ合って、最初のディーラーを決めよう。",
                "Compare with everyone and choose the first dealer.",
              )}
            </p>
          </>
        ) : (
          <div className="loading-state">
            <RefreshCw className="spin" aria-hidden="true" />
            {t("カードを確認中", "Checking your card")}
          </div>
        )}
        {isHost ? (
          <button
            className="primary-button"
            disabled={busy}
            onClick={() =>
              rpc("reset_poker_room", { target_room_id: room.id })
            }
          >
            <RotateCcw size={18} aria-hidden="true" />
            {t("同じメンバーでもう一度", "Play again")}
          </button>
        ) : null}
      </section>
    );
  }

  return (
    <section className="lobby">
      <div className="lobby-heading">
        <div>
          <p>{isHost ? "HOST LOBBY" : "WAITING ROOM"}</p>
          <h1>{t("テーブルコード", "Table code")}</h1>
        </div>
        <button
          className="room-code"
          title={t("URLをコピー", "Copy link")}
          onClick={() => navigator.clipboard.writeText(shareUrl)}
        >
          {room.code}
          <Copy size={18} aria-hidden="true" />
        </button>
      </div>

      <div className="lobby-status">
        <span>
          <UsersRound size={18} aria-hidden="true" />
          {members.length} / {room.capacity}
        </span>
        <span className={room.locked ? "locked" : "open"}>
          {room.locked ? <Lock size={16} /> : <LockOpen size={16} />}
          {room.locked
            ? t("参加締切", "Locked")
            : t("参加受付中", "Open")}
        </span>
      </div>

      <ul className="member-list">
        {members.map((member) => (
          <li key={member.id}>
            <span className="member-seat">{member.seat_index + 1}</span>
            <strong>
              {member.name}
              {member.user_id === room.host_user_id ? (
                <small>{t("ホスト", "HOST")}</small>
              ) : null}
            </strong>
            <span className={member.ready ? "ready" : "not-ready"}>
              {member.ready ? <Check size={16} /> : null}
              {member.ready
                ? t("準備OK", "Ready")
                : t("準備中", "Waiting")}
            </span>
            {isHost && member.user_id !== userId ? (
              <button
                className="remove-button"
                title={t("退出させる", "Remove")}
                onClick={() =>
                  rpc("remove_poker_member", {
                    target_room_id: room.id,
                    target_user_id: member.user_id,
                  })
                }
              >
                <Trash2 size={17} aria-hidden="true" />
              </button>
            ) : null}
          </li>
        ))}
      </ul>

      <div className="lobby-actions">
        <button
          className={me?.ready ? "secondary-button" : "primary-button"}
          disabled={busy}
          onClick={() =>
            rpc("set_poker_ready", {
              target_room_id: room.id,
              is_ready: !me?.ready,
            })
          }
        >
          <Check size={18} aria-hidden="true" />
          {me?.ready
            ? t("準備を取り消す", "Cancel ready")
            : t("準備OK", "I'm ready")}
        </button>

        {isHost ? (
          <>
            <button
              className="secondary-button"
              disabled={busy}
              onClick={() =>
                rpc("set_poker_room_lock", {
                  target_room_id: room.id,
                  is_locked: !room.locked,
                })
              }
            >
              {room.locked ? <LockOpen size={18} /> : <Lock size={18} />}
              {room.locked
                ? t("参加受付を再開", "Reopen room")
                : t("参加を締め切る", "Lock room")}
            </button>
            <button
              className="deal-now-button"
              disabled={busy || !room.locked || !allReady}
              onClick={() =>
                rpc("deal_poker_room", { target_room_id: room.id })
              }
            >
              <Sparkles size={20} aria-hidden="true" />
              {t("カードを配る", "Deal cards")}
            </button>
          </>
        ) : null}
      </div>

      {isHost && (!room.locked || !allReady) ? (
        <p className="lobby-hint">
          {t(
            "2人以上が準備OKになったら参加を締め切って配札できます。",
            "When at least two players are ready, lock the room and deal.",
          )}
        </p>
      ) : null}
      {error ? <p className="error-message">{error}</p> : null}
    </section>
  );
}

function LanguageControl({
  language,
  setLanguage,
  compact = false,
}: {
  language: Language;
  setLanguage: (language: Language) => void;
  compact?: boolean;
}) {
  return (
    <div className={`language-control ${compact ? "compact" : ""}`}>
      <Globe2 size={17} aria-hidden="true" />
      <button
        className={language === "ja" ? "active" : ""}
        onClick={() => setLanguage("ja")}
      >
        日本語
      </button>
      <button
        className={language === "en" ? "active" : ""}
        onClick={() => setLanguage("en")}
      >
        EN
      </button>
    </div>
  );
}

function IconToggle({
  active,
  label,
  onClick,
  activeIcon: ActiveIcon,
  inactiveIcon: InactiveIcon,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
  activeIcon: typeof Music;
  inactiveIcon: typeof VolumeX;
}) {
  const Icon = active ? ActiveIcon : InactiveIcon;
  return (
    <button
      className={`icon-toggle ${active ? "active" : ""}`}
      onClick={onClick}
      title={label}
      aria-label={label}
      aria-pressed={active}
    >
      <Icon size={19} aria-hidden="true" />
    </button>
  );
}
