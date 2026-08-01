import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Eat.css';

function Eat() {
  const { user } = useUser();
  const [input, setInput] = useState('');
  const [known, setKnown] = useState([]);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api.listRecipes().then((res) => setKnown(res.data)).catch(() => {});
  }, []);

  const go = async (dishName) => {
    if (!dishName.trim()) return;
    setWorking(true);
    setError('');
    try {
      const res = await api.resolveDish(dishName.trim());
      localStorage.setItem('borrowed_pantry_pending_recipe', res.data.name);
      localStorage.setItem('borrowed_pantry_recipe_id', res.data.id);
      navigate('/stores');
    } catch {
      setError("Couldn't work that one out. Try another way of writing it.");
      setWorking(false);
    }
  };

  return (
    <div className="eat-page">
      <h1 className="eat-question">What are you planning to eat?</h1>

      <form
        className="eat-form"
        onSubmit={(e) => {
          e.preventDefault();
          go(input);
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="jollof rice, egusi soup, doro wat..."
          disabled={working}
          autoFocus
        />
        <button type="submit" disabled={working || !input.trim()}>
          {working ? 'Working it out...' : 'Go'}
        </button>
      </form>

      {error && <p className="eat-error">{error}</p>}

      {working && (
        <p className="eat-working">
          Give me a moment, I'm figuring out what goes into this one.
        </p>
      )}

      {!working && known.length > 0 && (
        <div className="eat-known">
          <p className="eat-known-label">Or something we already know:</p>
          <div className="eat-chips">
            {known.map((r) => (
              <button key={r.id} className="eat-chip" onClick={() => go(r.name)}>
                {r.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default Eat;