import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import './AlreadyHave.css';

function AlreadyHave() {
  const [items, setItems] = useState([]);
  const [checked, setChecked] = useState(new Set());
  const [removed, setRemoved] = useState(new Set());
  const [extras, setExtras] = useState([]);
  const [extraInput, setExtraInput] = useState('');
  const [budget, setBudget] = useState(
    localStorage.getItem('borrowed_pantry_budget') || '25'
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const recipeId = localStorage.getItem('borrowed_pantry_recipe_id');
  const recipeName = localStorage.getItem('borrowed_pantry_pending_recipe');

  useEffect(() => {
    if (!recipeId) {
      navigate('/cook');
      return;
    }
    api
      .getRecipeIngredients(recipeId)
      .then((res) => {
        setItems(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load ingredients.');
        setLoading(false);
      });
  }, [recipeId]);

  const toggleChecked = (name) => {
    setChecked((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const toggleRemoved = (name) => {
    setRemoved((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const addExtra = () => {
    const name = extraInput.trim();
    if (!name || extras.includes(name)) return;
    setExtras((prev) => [...prev, name]);
    setExtraInput('');
  };

  const removeExtra = (name) => {
    setExtras((prev) => prev.filter((e) => e !== name));
  };

  const handleContinue = () => {
    localStorage.setItem('borrowed_pantry_already_have', JSON.stringify(Array.from(checked)));
    localStorage.setItem('borrowed_pantry_excluded', JSON.stringify(Array.from(removed)));
    localStorage.setItem('borrowed_pantry_extras', JSON.stringify(extras));
    localStorage.setItem('borrowed_pantry_budget', String(budget));
    navigate('/plan');
  };

  if (loading) return <div className="have-page">Loading...</div>;
  if (error) return <div className="have-page">{error}</div>;

  return (
    <div className="have-page">
      <h2 className="page-title">{recipeName}</h2>
      <p className="page-subtitle">Check what you have. Remove what you don't want. Add what's missing.</p>

      <div className="have-list">
        {items.map((item) => (
          <div key={item.id} className={removed.has(item.name) ? 'have-row have-row-removed' : 'have-row'}>
            <label className="have-row-label">
              <input
                type="checkbox"
                checked={checked.has(item.name)}
                disabled={removed.has(item.name)}
                onChange={() => toggleChecked(item.name)}
              />
              <span>{item.name}</span>
            </label>
            <button
              type="button"
              className="remove-toggle"
              onClick={() => toggleRemoved(item.name)}
            >
              {removed.has(item.name) ? 'Undo' : 'Remove'}
            </button>
          </div>
        ))}
      </div>

      <div className="extras-block">
        <p className="section-label">Add something extra</p>
        <div className="extra-input-row">
          <input
            type="text"
            value={extraInput}
            onChange={(e) => setExtraInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addExtra())}
            placeholder="e.g. crab, extra pepper..."
          />
          <button type="button" onClick={addExtra}>Add</button>
        </div>
        {extras.length > 0 && (
          <div className="extra-chips">
            {extras.map((name) => (
              <span key={name} className="extra-chip">
                {name}
                <button type="button" onClick={() => removeExtra(name)}>&times;</button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="budget-block">
        <label className="section-label" htmlFor="budget-input">Budget</label>
        <div className="budget-input-row">
          <span className="budget-currency">$</span>
          <input
            id="budget-input"
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            min="0"
            step="0.01"
          />
        </div>
      </div>

      <button className="continue-button" onClick={handleContinue}>
        See my plan
      </button>
    </div>
  );
}

export default AlreadyHave;