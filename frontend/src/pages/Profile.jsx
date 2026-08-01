import { useState } from 'react';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Login.css';

const DIETARY_OPTIONS = [
  'Vegetarian', 'No pork', 'No beef', 'Nut allergy',
  'Shellfish allergy', 'Dairy-free', 'Gluten-free',
];

function Profile() {
  const { user, setUser } = useUser();
  const [restrictions, setRestrictions] = useState(user?.dietary_restrictions || []);
  const [budget, setBudget] = useState(user?.default_budget ?? '');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');

  const toggleRestriction = (option) => {
    setRestrictions((prev) =>
      prev.includes(option) ? prev.filter((r) => r !== option) : [...prev, option]
    );
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.upsertProfile({
        email: user.email,
        name: user.name,
        default_budget: budget === '' ? null : parseFloat(budget),
        dietary_restrictions: restrictions,
      });
      setUser({
        ...user,
        default_budget: budget === '' ? null : parseFloat(budget),
        dietary_restrictions: restrictions,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError('Could not save. Try again.');
    }
  };

  if (!user) return <div>Log in first.</div>;

  return (
    <div className="login-page" style={{ padding: '20px 0' }}>
      <h2 className="page-title">Your details</h2>
      <form className="login-form" onSubmit={handleSave}>
        <label>
          Weekly grocery budget
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
          <legend>Allergies and restrictions</legend>
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
        <button type="submit">{saved ? 'Saved' : 'Save changes'}</button>
      </form>
    </div>
  );
}

export default Profile;