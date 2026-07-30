import { useEffect, useState } from 'react';
import { useUser } from '../UserContext';
import { api } from '../api';
import './History.css';

function History() {
  const { user } = useUser();
  const [entries, setEntries] = useState([]);
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

  if (loading) return <div className="history-page">Loading...</div>;
  if (error) return <div className="history-page">{error}</div>;

  return (
    <div className="history-page">
      <h2 className="page-title">History</h2>
      <p className="page-subtitle">Everything you've already pulled off.</p>

      {entries.length === 0 ? (
        <p className="history-empty">
          Nothing yet. Cook something, mark it done, and it'll live here.
        </p>
      ) : (
        <div className="history-list">
          {entries.map((entry) => (
            <div key={entry.id} className="history-card">
              <div className="history-card-top">
                <span className="history-recipe-name">{entry.recipe_name}</span>
                <span className="history-date">{formatDate(entry.cooked_at)}</span>
              </div>
              {entry.store_name && (
                <p className="history-store">Shopped at {entry.store_name}</p>
              )}
              {entry.notes && <p className="history-notes">{entry.notes}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default History;