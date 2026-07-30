import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Shopping.css';

function Shopping() {
  const [items, setItems] = useState([]);
  const [checked, setChecked] = useState(new Set());
  const navigate = useNavigate();

  useEffect(() => {
    const raw = localStorage.getItem('borrowed_pantry_basket');
    if (!raw) {
      navigate('/plan');
      return;
    }
    setItems(JSON.parse(raw));
  }, []);

  const toggle = (name) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const allChecked = items.length > 0 && checked.size === items.length;

  return (
    <div className="shopping-page">
      <h2 className="page-title">Shopping list</h2>
      <p className="page-subtitle">Check things off as you grab them.</p>

      <div className="shopping-list">
        {items.map((item, i) => (
          <label
            key={i}
            className={checked.has(item.using) ? 'shopping-row shopping-row-checked' : 'shopping-row'}
          >
            <input
              type="checkbox"
              checked={checked.has(item.using)}
              onChange={() => toggle(item.using)}
            />
            <span className="shopping-item-name">{item.using}</span>
            <span className="shopping-item-price">${item.price.toFixed(2)}</span>
          </label>
        ))}
      </div>

      <button
        className="continue-button"
        disabled={!allChecked}
        onClick={() => navigate('/steps')}
      >
        {allChecked ? 'Got everything — get cooking steps' : `${checked.size} of ${items.length} checked`}
      </button>
    </div>
  );
}

export default Shopping;