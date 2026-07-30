import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Cook.css';

function Cook() {
  const { user } = useUser();
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [budget, setBudget] = useState(user?.default_budget ?? 25);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .listRecipes()
      .then((res) => {
        setRecipes(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load recipes.');
        setLoading(false);
      });
  }, []);

  const handleContinue = () => {
    if (!selectedRecipe) return;
    localStorage.setItem('borrowed_pantry_pending_recipe', selectedRecipe.name);
    localStorage.setItem('borrowed_pantry_recipe_id', selectedRecipe.id);
    localStorage.setItem('borrowed_pantry_budget', String(budget));
    navigate('/have');
  };

  if (loading) return <div className="cook-page">Loading recipes...</div>;
  if (error) return <div className="cook-page">{error}</div>;

  return (
    <div className="cook-page">
      <h2 className="page-title">What are you cooking?</h2>
      <p className="page-subtitle">Pick the dish. Set the budget.</p>

      <div className="recipe-list">
        {recipes.map((recipe) => (
          <button
            key={recipe.id}
            className={
              selectedRecipe?.id === recipe.id ? 'recipe-card recipe-card-selected' : 'recipe-card'
            }
            onClick={() => setSelectedRecipe(recipe)}
          >
            <div className="recipe-card-top">
              <span className="recipe-name">{recipe.name}</span>
              <span className="recipe-cuisine">{recipe.cuisine}</span>
            </div>
            <p className="recipe-description">{recipe.description}</p>
            <span className="recipe-time">{recipe.est_time_minutes} min</span>
          </button>
        ))}
      </div>

      {selectedRecipe && (
        <div className="budget-block">
          <label className="budget-label" htmlFor="budget-input">
            Budget for this shop
          </label>
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
          <button className="continue-button" onClick={handleContinue}>
            Continue
          </button>
        </div>
      )}
    </div>
  );
}

export default Cook;