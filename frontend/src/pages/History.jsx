import { useEffect, useState } from 'react';
import { useUser } from '../UserContext';
import { api } from '../api';
import './History.css';

function History() {
  const { user } = useUser();
  const [entries, setEntries] = useState([]);
  const [openId, setOpenId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) return;
    api
      .getCookedHistory(user.id)
      .then((res) => {
        setEntries(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load your history.');
        setLoading(false);
      });
  }, [user]);

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (loading) {
    return <div className="history-page">Loading...</div>;
  }

  if (error) {
    return <div className="history-page">{error}</div>;
  }

  return (
    <div className="history-page">
      <h2 className="page-title">Already Cooked</h2>
      <p className="page-subtitle">Everything you've already pulled off.</p>
      {entries.length === 0 ? (
        <p className="history-empty">
          Nothing yet. Cook something, mark it done, and it'll live here.
        </p>
      ) : (
        <div className="history-list">
          {entries.map(function (entry) {
            return (
              <HistoryCard
                key={entry.id}
                entry={entry}
                isOpen={openId === entry.id}
                onToggle={function () {
                  setOpenId(openId === entry.id ? null : entry.id);
                }}
                formatDate={formatDate}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function HistoryCard(props) {
  const entry = props.entry;
  return (
    <div className="history-card">
      <button className="history-card-header" onClick={props.onToggle}>
        <div className="history-card-top">
          <span className="history-recipe-name">{entry.recipe_name}</span>
          <span className="history-date">{props.formatDate(entry.cooked_at)}</span>
        </div>
        {entry.store_name ? (
          <p className="history-store">Shopped at {entry.store_name}</p>
        ) : null}
      </button>
      {props.isOpen ? <HistoryDetail entry={entry} /> : null}
    </div>
  );
}

function HistoryDetail(props) {
  const entry = props.entry;
  const hasBasket = entry.basket && entry.basket.length > 0;

  return (
    <div className="history-detail">
      {entry.cuisine ? (
        <p className="detail-meta">
          {entry.cuisine}
          {entry.est_time_minutes ? ' - ' + entry.est_time_minutes + ' min' : ''}
        </p>
      ) : null}

      {hasBasket ? (
        <div>
          <p className="detail-label">What you bought</p>
          <div className="detail-basket">
            {entry.basket.map(function (item, i) {
              return (
                <div key={i} className="detail-basket-row">
                  <span>{item.using}</span>
                  <span className="detail-price">${Number(item.price).toFixed(2)}</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="detail-meta">No shopping list saved for this one.</p>
      )}

      {hasBasket && entry.total !== null && entry.total !== undefined ? (
        <div className="detail-total-row">
          <span>Total</span>
          <span>${Number(entry.total).toFixed(2)}</span>
        </div>
      ) : null}

      {entry.video_url ? <a href={entry.video_url} target="_blank" rel="noreferrer" className="detail-video-link">Watch how to make it again</a> : null}
    </div>
  );
}

export default History;