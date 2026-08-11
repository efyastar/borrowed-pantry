import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { distanceMiles } from '../utils/geo';
import './Stores.css';

function Stores() {
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [locationStatus, setLocationStatus] = useState('locating');
  const [preparing, setPreparing] = useState(null);
  const [selectedStore, setSelectedStore] = useState(
    localStorage.getItem('borrowed_pantry_selected_store') || null
  );
  const navigate = useNavigate();

  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationStatus('unsupported');
      loadFallback();
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        api
          .storesNearby(latitude, longitude)
          .then((res) => {
            const withDistance = res.data
              .map((s) => ({
                ...s,
                distance: s.lat && s.lng ? distanceMiles(latitude, longitude, s.lat, s.lng) : null,
              }))
              .filter((s) => s.distance === null || s.distance < 40)
              .sort((a, b) => (a.distance ?? Infinity) - (b.distance ?? Infinity));
            setStores(withDistance.length ? withDistance : res.data);
            setLocationStatus('found');
            setLoading(false);
          })
          .catch(() => {
            setError('Could not load stores.');
            setLoading(false);
          });
      },
      () => {
        setLocationStatus('denied');
        loadFallback();
      }
    );
  }, []);

  const loadFallback = () => {
    api
      .listStores()
      .then((res) => {
        setStores(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load stores.');
        setLoading(false);
      });
  };

  const handleSelect = async (store) => {
    setSelectedStore(store.name);
    localStorage.setItem('borrowed_pantry_selected_store', store.name);
    setPreparing(store.id);
    try {
      await api.ensureInventory(store.id);
    } catch {
      // Fall through anyway; the plan will show what it can
    }
    navigate('/have');
  };

  if (loading) return <div className="stores-page">Finding stores near you...</div>;
  if (error) return <div className="stores-page">{error}</div>;

  return (
    <div className="stores-page">
      <h2 className="page-title">Stores</h2>
      <p className="page-subtitle">Closest first. Always your call.</p>

      {locationStatus === 'denied' && (
        <p className="location-note">No location, no problem. Just pick one.</p>
      )}
      {locationStatus === 'unsupported' && (
        <p className="location-note">Can't read your location here. Pick manually.</p>
      )}

      <div className="store-list">
        {stores.map((store) => (
          <button
            key={store.id}
            className={
              selectedStore === store.name ? 'store-card store-card-selected' : 'store-card'
            }
            onClick={() => handleSelect(store)}
            disabled={preparing !== null}
          >
            <div className="store-card-top">
              <span className="store-name">{store.name}</span>
              {store.distance !== null && store.distance !== undefined && (
                <span className="store-distance">{store.distance.toFixed(1)} mi</span>
              )}
            </div>
            <p className="store-address">{store.address}</p>
            <div className="store-tags">
              {store.store_type === 'african' && <span className="tag">Specialty market</span>}
              {store.on_ubereats && <span className="tag">Uber Eats</span>}
              {store.on_doordash && <span className="tag">DoorDash</span>}
            </div>
            {preparing === store.id && (
              <span className="selected-tag">Checking what they stock...</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

export default Stores;