import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Login.css';

const DIETARY_OPTIONS = [
  'Vegetarian',
  'No pork',
  'No beef',
  'Nut allergy',
  'Shellfish allergy',
  'Dairy-free',
  'Gluten-free',
];

function Login() {
  const [step, setStep] = useState('identify');
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [restrictions, setRestrictions] = useState([]);
  const [budget, setBudget] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { setUser } = useUser();
  const navigate = useNavigate();

  const toggleRestriction = (option) => {
    setRestrictions((prev) =>
      prev.includes(option) ? prev.filter((r) => r !== option) : [...prev, option]
    );
  };

  const handleIdentify = async (e) => {
    e.preventDefault();
    if (!email.trim() || !name.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.getProfile(email.trim());
      setUser(res.data);
      navigate('/stores');
    } catch (err) {
      if (err.response && err.response.status === 404) {
        setStep('setup');
      } else {
        setError('Something went wrong. Try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSetup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.upsertProfile({
        email: email.trim(),
        name: name.trim(),
        default_budget: budget ? parseFloat(budget) : null,
        dietary_restrictions: restrictions,
      });
      setUser({
        id: res.data.user_id,
        email: email.trim(),
        name: name.trim(),
        default_budget: budget ? parseFloat(budget) : null,
        dietary_restrictions: restrictions,
      });
      navigate('/eat');
    } catch (err) {
      setError('Something went wrong. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <h1 className="login-title">The Borrowed Pantry</h1>
      <p className="login-tagline">Recipe apps tell you what to cook.<br />We remember what worked.</p>

      {step === 'identify' && (
        <form className="login-form" onSubmit={handleIdentify}>
          <label>
            Name
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Afia"
              required
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </label>
          {error && <p className="login-error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Checking...' : 'Continue'}
          </button>
        </form>
      )}

      {step === 'setup' && (
        <form className="login-form" onSubmit={handleSetup}>
          <p className="setup-intro">Hey, {name}. Two quick things, then we cook.</p>

          <label>
            Weekly grocery budget (optional)
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="25"
              min="0"
              step="0.01"
            />
          </label>

          <fieldset className="dietary-fieldset">
            <legend>Anything you can't eat?</legend>
            <div className="dietary-grid">
              {DIETARY_OPTIONS.map((option) => (
                <button
                  type="button"
                  key={option}
                  className={restrictions.includes(option) ? 'chip chip-active' : 'chip'}
                  onClick={() => toggleRestriction(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </fieldset>

          {error && <p className="login-error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : 'Start cooking'}
          </button>
        </form>
      )}
    </div>
  );
}

export default Login;