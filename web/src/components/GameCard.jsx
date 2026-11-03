import { formatCount, gameHref, gameName, scoreColor, steamPct } from "../lib/games.js";

// Cover art: the portrait library image, else the banner on a blurred backdrop, with an optional corner badge
function Cover({ game, name, badge }) {
  const label = badge && <span className="game-badge">{badge}</span>;
  if (game.library_image) {
    return <div className="game-cover"><img src={game.library_image} alt={name} loading="lazy" />{label}</div>;
  }
  if (game.header_image) {
    return (
      <div className="game-cover">
        <img className="backdrop" src={game.header_image} alt="" loading="lazy" />
        <img className="front" src={game.header_image} alt={name} loading="lazy" />
        {label}
      </div>
    );
  }
  return <div className="game-cover empty">{name}{label}</div>;
}

// One library card with cover art, name, Steam score and a note, the review count unless given
export default function GameCard({ game, note, badge }) {
  const name = gameName(game);
  const pct = steamPct(game);
  return (
    <a className="game-card" href={gameHref(game.appid)}>
      <Cover game={game} name={name} badge={badge} />
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
