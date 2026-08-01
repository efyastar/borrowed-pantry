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
  const [selectedStore, setSelectedStore] = useState(
    localStorage.getItem('borrowed_pantry_selected_store') || null
  );
  const navigate = useNavigate();

  useEffect(() => {
    api
      .listStores()
      .then((res) => {
        setStores(res.data);
        setLoading(false);
        locateAndSort(res.data);
      })
      .catch(() => {
        setError('Could not load stores.');
        setLoading(false);
      });
  }, []);

  const locateAndSort = (storeList) => {
    if (!navigator.geolocation) {
      setLocationStatus('unsupported');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        const withDistance = storeList.map((s) => ({
          ...s,
          distance: s.lat && s.lng ? distanceMiles(latitude, longitude, s.lat, s.lng) : null,
        }));
        withDistance.sort((a, b) => (a.distance ?? Infinity) - (b.distance ?? Infinity));
        setStores(withDistance);
        setLocationStatus('found');
      },
      () => {
        setLocationStatus('denied');
      }
    );
  };

  const handleSelect = (store) => {
    setSelectedStore(store.name);
    localStorage.setItem('borrowed_pantry_selected_store', store.name);
    navigate('/have');
  };

  if (loading) return <div className="stores-page">Loading stores...</div>;
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
      {locationStatus === 'locating' && (
        <p className="location-note">Finding what's close...</p>
      )}

      <div className="store-list">
        {stores.map((store) => (
          <button
            key={store.id}
            className={
              selectedStore === store.name ? 'store-card store-card-selected' : 'store-card'
            }
            onClick={() => handleSelect(store)}
          >
            <div className="store-card-top">
              <span className="store-name">{store.name}</span>
              {store.distance !== null && store.distance !== undefined && (
                <span className="store-distance">{store.distance.toFixed(1)} mi</span>
              )}
            </div>
            <p className="store-address">{store.address}</p>
            <div className="store-tags">
              {store.store_type === 'african' && <span className="tag">African market</span>}
              {store.on_ubereats && <span className="tag">Uber Eats</span>}
              {store.on_doordash && <span className="tag">DoorDash</span>}
              {!store.on_ubereats && !store.on_doordash && (
                <span className="tag tag-muted">Pickup only</span>
              )}
            </div>
            {selectedStore === store.name && <span className="selected-tag">This one</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

export default Stores;