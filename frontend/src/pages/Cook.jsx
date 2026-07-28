import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import './Cook.css';

function Cook() {
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
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

  const handlePlan = (recipe) => {
    localStorage.setItem('borrowed_pantry_pending_recipe', recipe.name);
    navigate('/chat');
  };

  if (loading) {
    return <div className="cook-page">Loading recipes...</div>;
  }

  if (error) {
    return <div className="cook-page">{error}</div>;
  }

  return (
    <div className="cook-page">
      <h2 className="page-title">Cook Something</h2>
      <p className="page-subtitle">Pick a dish and I'll help you shop for it.</p>
      <div className="recipe-list">
        {recipes.map(function (recipe) {
          return (
            <div key={recipe.id} className="recipe-card">
              <div className="recipe-card-top">
                <span className="recipe-name">{recipe.name}</span>
                <span className="recipe-cuisine">{recipe.cuisine}</span>
              </div>
              <p className="recipe-description">{recipe.description}</p>
              <div className="recipe-card-bottom">
                <span className="recipe-time">{recipe.est_time_minutes} min</span>
                <RecipeVideoLink url={recipe.video_url} />
              </div>
              <button className="recipe-plan-button" onClick={function () { handlePlan(recipe); }}>
                Plan this dish
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RecipeVideoLink(props) {
  if (!props.url) {
    return null;
  }
  return (
    <a href={props.url} target="_blank" rel="noopener noreferrer" className="recipe-video-link">
      Watch a video
    </a>
  );
}

export default Cook;