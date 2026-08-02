import { useEffect, useState } from 'react';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Community.css';

function Community() {
  const { user } = useUser();
  const [tips, setTips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');

  const [search, setSearch] = useState('');
  const [matches, setMatches] = useState([]);
  const [picked, setPicked] = useState(null);
  const [substitute, setSubstitute] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [recipes, setRecipes] = useState([]);
  const [recipeId, setRecipeId] = useState('');

  const loadTips = () => {
    api
      .listCommunityTips()
      .then((res) => {
        setTips(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load tips.');
        setLoading(false);
      });
  };

  useEffect(loadTips, []);

  useEffect(() => {
    api.listRecipes().then((res) => setRecipes(res.data)).catch(() => {});
  }, []);

  useEffect(() => {
    if (search.trim().length < 2) {
      setMatches([]);
      return;
    }
    api
      .searchIngredients(search.trim())
      .then((res) => setMatches(res.data))
      .catch(() => setMatches([]));
  }, [search]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!picked || !substitute.trim() || !notes.trim()) return;
    setSaving(true);
    try {
      await api.submitTip({
        user_id: user.id,
        original_ingredient_id: picked.id,
        substitute_name: substitute.trim(),
        notes: notes.trim(),
        recipe_id: recipeId || null,
      });
      setPicked(null);
      setSearch('');
      setSubstitute('');
      setNotes('');
      setRecipeId('');
      setAdding(false);
      setSaving(false);
      setLoading(true);
      loadTips();
    } catch {
      setError('Could not save your tip.');
      setSaving(false);
    }
  };

  return (
    <div className="community-page">
      <h2 className="page-title">Community</h2>
      <p className="page-subtitle">What other people found that works.</p>

      {!adding ? (
        <button className="add-tip-button" onClick={() => setAdding(true)}>
          Share what worked for you
        </button>
      ) : (
        <form className="tip-form" onSubmit={handleSubmit}>
          <label>
            What was hard to find?
            <input
              type="text"
              value={picked ? picked.name : search}
              onChange={(e) => {
                setPicked(null);
                setSearch(e.target.value);
              }}
              placeholder="egusi, palm oil, garden eggs..."
            />
          </label>

          {!picked && matches.length > 0 && (
            <div className="match-list">
              {matches.map((m) => (
                <button
                  type="button"
                  key={m.id}
                  className="match-item"
                  onClick={() => {
                    setPicked(m);
                    setMatches([]);
                  }}
                >
                  {m.name}
                </button>
              ))}
            </div>
          )}

          <label>
            What did you use instead?
            <input
              type="text"
              value={substitute}
              onChange={(e) => setSubstitute(e.target.value)}
              placeholder="pumpkin seeds"
            />
          </label>

          <label>
            What were you making?
            <select value={recipeId} onChange={(e) => setRecipeId(e.target.value)}>
              <option value="">Any dish</option>
              {recipes.map((r) => (
                <option key={r.id} value={r.id}>{r.name}</option>
              ))}
            </select>
          </label>

          <label>
            Why does it work?
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Grind them first. Milder than the real thing but thickens the same way."
              rows={4}
            />
          </label>

          {error && <p className="community-error">{error}</p>}

          <div className="tip-form-actions">
            <button type="submit" disabled={saving || !picked || !substitute.trim() || !notes.trim()}>
              {saving ? 'Sharing...' : 'Share it'}
            </button>
            <button type="button" className="cancel-button" onClick={() => setAdding(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="community-loading">Loading...</p>
      ) : tips.length === 0 ? (
        <p className="community-empty">
          Nobody's shared anything yet. Be the first one.
        </p>
      ) : (
        <div className="tip-list">
          {tips.map((tip) => (
            <div key={tip.id} className="tip-card">
              <p className="tip-swap">
                {tip.substitute} <span className="tip-arrow">instead of</span> {tip.original}
              </p>
              <p className="tip-notes">{tip.notes}</p>
              <p className="tip-author">
                {tip.author}
                {tip.recipe_name ? ` · while making ${tip.recipe_name}` : ''}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default Community;