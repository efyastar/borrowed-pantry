import { useEffect, useState } from 'react';
import { api } from '../api';
import { useUser } from '../UserContext';
import './Steps.css';

function Steps() {
  const { user } = useUser();
  const [steps, setSteps] = useState('');
  const [videoUrl, setVideoUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const recipe = localStorage.getItem('borrowed_pantry_pending_recipe');
    if (!recipe || !user) return;

    api
      .listRecipes()
      .then((res) => {
        const match = res.data.find((r) => r.name === recipe);
        if (match) setVideoUrl(match.video_url);
      })
      .catch(() => {});

    api
      .sendChat({
        email: user.email,
        name: user.name,
        message: `Give me only the cooking steps for ${recipe}. No shopping list, no prices, just the method, numbered.`,
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

  return (
    <div className="steps-page">
      <h2 className="page-title">Cooking steps</h2>

      {videoUrl && (
        <a href={videoUrl} target="_blank" rel="noopener noreferrer" className="video-link">
          Watch a video version
        </a>
      )}

      {loading && <p className="steps-loading">Writing out the method...</p>}
      {error && <p className="steps-loading">{error}</p>}
      {!loading && !error && <div className="steps-text">{steps}</div>}
    </div>
  );
}

export default Steps;