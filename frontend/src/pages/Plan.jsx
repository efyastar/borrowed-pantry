import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Plan.css';

function Plan() {
  const { user } = useUser();
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const recipe = localStorage.getItem('borrowed_pantry_pending_recipe');
    const store = localStorage.getItem('borrowed_pantry_selected_store');
    const budget = parseFloat(localStorage.getItem('borrowed_pantry_budget') || '25');
    const alreadyHaveRaw = localStorage.getItem('borrowed_pantry_already_have');
    const alreadyHave = alreadyHaveRaw ? JSON.parse(alreadyHaveRaw) : [];
    const excludedRaw = localStorage.getItem('borrowed_pantry_excluded');
    const excluded = excludedRaw ? JSON.parse(excludedRaw) : [];
    const extrasRaw = localStorage.getItem('borrowed_pantry_extras');
    const extras = extrasRaw ? JSON.parse(extrasRaw) : [];

    if (!recipe || !store || !user) {
      navigate('/cook');
      return;
    }

    api
      .getPlan({
        email: user.email,
        name: user.name,
        recipe,
        store,
        budget,
        already_have: alreadyHave,
        excluded_ingredients: excluded,
        extra_ingredients: extras,
      })
      .then((res) => {
        setPlan(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not build a plan. Try a different store.');
        setLoading(false);
      });
  }, [user]);

  const handleGoShopping = () => {
    localStorage.setItem('borrowed_pantry_basket', JSON.stringify(plan.final_items));
    navigate('/shopping');
  };

  if (loading) return <div className="plan-page">Building your basket...</div>;
  if (error) return <div className="plan-page">{error}</div>;
  if (!plan) return null;

  return (
    <div className="plan-page">
      <h2 className="page-title">{plan.recipe}</h2>
      <p className="page-subtitle">at {plan.store}</p>

      {plan.allergy_substitutions_applied?.length > 0 && (
        <p className="plan-note">
          Swapped for your allergies: {plan.allergy_substitutions_applied.join(', ')}
        </p>
      )}
      {plan.excluded_by_user?.length > 0 && (
        <p className="plan-note">Removed: {plan.excluded_by_user.join(', ')}</p>
      )}

      <div className="basket-list">
        {plan.final_items.map((item, i) => (
          <div key={i} className="basket-row">
            <div className="basket-row-top">
              <span className="basket-item-name">{item.using}</span>
              <span className="basket-item-price">${item.price.toFixed(2)}</span>
            </div>
            {item.reason && (
              <div className="basket-item-reason">
                <span className={item.source === 'community' ? 'reason-tag reason-tag-community' : 'reason-tag'}>
                  {item.source === 'community' ? `shared by ${item.author}` : 'verified substitution'}
                </span>
                <p className="reason-text">{item.reason}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="basket-total-row">
        <span>Total</span>
        <span>${plan.final_total.toFixed(2)}</span>
      </div>

      {!plan.fits_budget && (
        <p className="plan-warning">
          ${plan.over_by.toFixed(2)} over budget — essentials alone exceed what you set.
        </p>
      )}

      {plan.removed_optional.length > 0 && (
        <p className="plan-note">
          Left out to stay in budget: {plan.removed_optional.map((o) => o.ingredient).join(', ')}
        </p>
      )}

      {plan.unavailable_essentials.length > 0 && (
        <p className="plan-warning">
          Not available at this store, no substitute either: {plan.unavailable_essentials.join(', ')}
        </p>
      )}

      {plan.other_store_options.length > 0 && (
        <div className="other-stores">
          <p className="plan-note-label">The real thing, elsewhere:</p>
          {plan.other_store_options.map((opt, i) => (
            <p key={i} className="other-store-row">
              {opt.ingredient} — {opt.store} (${opt.price.toFixed(2)})
            </p>
          ))}
        </div>
      )}

      <button className="continue-button" onClick={handleGoShopping}>
        Start shopping
      </button>
    </div>
  );
}

export default Plan;