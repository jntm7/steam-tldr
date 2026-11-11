import { formatCount, gameHref, gameName, scoreColor, steamPct } from "../lib/games.js";

// Cover art: the portrait library image, else the banner on a blurred backdrop, with an optional corner badge
function Cover({ game, name, badge, eager, children }) {
  const loading = eager ? "eager" : "lazy";
  const label = <>{badge && <span className="game-badge">{badge}</span>}{children}</>;
  if (game.library_image) {
    return <div className="game-cover"><img src={game.cover ?? game.library_image} alt={name} width="240" height="360" loading={loading} decoding="async" />{label}</div>;
  }
  if (game.header_image) {
    const banner = game.banner ?? game.header_image;
    return (
      <div className="game-cover">
        <img className="backdrop" src={banner} alt="" width="240" height="112" loading={loading} decoding="async" />
        <img className="front" src={banner} alt={name} width="240" height="112" loading={loading} decoding="async" />
        {label}
      </div>
    );
  }
  return <div className="game-cover empty">{name}{label}</div>;
}

// Score badge in the cover's corner and, on hover, the rating label, review count and genres
function CoverDetails({ game, pct }) {
  const genres = (game.genres ?? []).slice(0, 2).join(", ");
  return (
    <>
      <span className="game-score-badge" style={{ color: pct === null ? undefined : scoreColor(pct) }}>{pct === null ? "—" : `${pct.toFixed(0)}%`}</span>
      <span className="game-hover">
        <b>{pct === null ? "No reviews yet" : game.summary.review_score_desc}</b>
        {pct !== null && <span>{formatCount(game.summary.total_reviews)} reviews</span>}
        {genres && <span>{genres}</span>}
      </span>
    </>
  );
}

// One library card with cover art, name, Steam score and a note, the review count unless given;
// compact cards move the score onto the cover and keep only the name below; eager cards load their art at once (for ones above the fold)
export default function GameCard({ game, note, badge, compact = false, eager = false }) {
  const name = gameName(game);
  const pct = steamPct(game);
  if (compact) {
    const title = pct === null ? name : `${name}: ${pct.toFixed(0)}% ${game.summary.review_score_desc}, ${formatCount(game.summary.total_reviews)} reviews`;
    return (
      <a className="game-card compact" href={gameHref(game.appid)} title={title}>
        <Cover game={game} name={name} eager={eager}><CoverDetails game={game} pct={pct} /></Cover>
        <div className="game-label"><span>{name}</span></div>
      </a>
    );
  }
  return (
    <a className="game-card" href={gameHref(game.appid)}>
      <Cover game={game} name={name} badge={badge} eager={eager} />
      <div className="game-name">{name}</div>
      {pct === null ? (
        <div className="game-score">No reviews yet</div>
      ) : (
        <>
          <div className="game-score" style={{ color: scoreColor(pct) }}>{pct.toFixed(0)}% · {game.summary.review_score_desc}</div>
          <div className="game-reviews">{note ?? `${formatCount(game.summary.total_reviews)} reviews`}</div>
        </>
      )}
    </a>
  );
}
