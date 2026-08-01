import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Steps.css';

function Steps() {
  const { user } = useUser();
  const [steps, setSteps] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [logging, setLogging] = useState(false);
  const navigate = useNavigate();

  const recipeName = localStorage.getItem('borrowed_pantry_pending_recipe');
  const recipeId = localStorage.getItem('borrowed_pantry_recipe_id');

  useEffect(() => {
    if (!recipeName || !user) return;

    api
      .listRecipes()
      .then((res) => {
        const match = res.data.find((r) => r.name === recipeName);
        if (match) setVideoUrl(match.video_url);
      })
      .catch(() => {});

    api
      .sendChat({
        email: user.email,
        name: user.name,
        message: `Give me only the cooking steps for ${recipeName}. No shopping list, no prices, just the method, numbered.`,
      })
      .then((res) => {
        setSteps(res.data.reply);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load the steps. Try again.');
        setLoading(false);
      });
  }, [user]);

  const handleDoneCooking = async () => {
    if (!user || !recipeId) return;
    setLogging(true);
    const storeName = localStorage.getItem('borrowed_pantry_selected_store') || null;
    const basketRaw = localStorage.getItem('borrowed_pantry_basket');
    const basket = basketRaw ? JSON.parse(basketRaw) : [];
    const total = basket.reduce((sum, item) => sum + (item.price || 0), 0);
    try {
      await api.logCooked({
        user_id: user.id,
        recipe_id: recipeId,
        store_name: storeName,
        notes: null,
        basket,
        total: Math.round(total * 100) / 100,
      });
      navigate('/history');
    } catch {
      setError('Could not save that. Try again.');
      setLogging(false);
    }
  };

  return (
    <div className="steps-page">
      <h2 className="page-title">{recipeName}</h2>

      {videoUrl && (
        <a href={videoUrl} target="_blank" rel="noopener noreferrer" className="video-link">
          Watch a video version
        </a>
      )}

      {loading && <p className="steps-loading">Writing out the method...</p>}
      {error && <p className="steps-loading">{error}</p>}
      {!loading && !error && <div className="steps-text">{steps}</div>}

      {!loading && !error && (
        <button className="done-button" onClick={handleDoneCooking} disabled={logging}>
          {logging ? 'Saving...' : 'Done cooking'}
        </button>
      )}
    </div>
  );
}

export default Steps;