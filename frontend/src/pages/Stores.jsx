import { useEffect, useState } from 'react';
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
  };

  if (loading) return <div className="stores-page">Loading stores...</div>;
  if (error) return <div className="stores-page">{error}</div>;

  return (
    <div className="stores-page">
      <h2 className="page-title">Stores</h2>

      {locationStatus === 'denied' && (
        <p className="location-note">
          Location access was denied, so distances aren't shown. You can still browse and pick a store below.
        </p>
      )}
      {locationStatus === 'unsupported' && (
        <p className="location-note">Your browser doesn't support location. Distances aren't shown.</p>
      )}
      {locationStatus === 'locating' && (
        <p className="location-note">Finding stores near you...</p>
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
              {store.store_type === 'african' && <span className="badge badge-african">African</span>}
            </div>
            <p className="store-address">{store.address}</p>
            {store.distance !== null && store.distance !== undefined && (
              <p className="store-distance">{store.distance.toFixed(1)} mi away</p>
            )}
            {selectedStore === store.name && <span className="selected-tag">Selected for shopping</span>}
          </button>
        ))}
      </div>
    </div>
  );
}

export default Stores;