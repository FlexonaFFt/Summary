import { useState } from 'react';
import '../styles/homepage.css';

interface HomePageProps {
  onStart: () => void;
}

const HomePage: React.FC<HomePageProps> = ({ onStart }) => {
  const [activeTab, setActiveTab] = useState('local');

  return (
    <div className="homepage-container">
      <div className="header-container">
        <div className="logo-wrapper">
          <h2 className="logo-text">Popcorn</h2>
          <button className="cta-button-small" onClick={() => {
            console.log('Get the app button clicked');
            onStart();
          }}>Get the app</button>
        </div>
      </div>

      <div className="tabs-container">
        <button 
          className={`tab-button ${activeTab === 'local' ? 'active' : ''}`}
          onClick={() => setActiveTab('local')}
        >
          Local
        </button>
        <button 
          className={`tab-button ${activeTab === 'regional' ? 'active' : ''}`}
          onClick={() => setActiveTab('regional')}
        >
          Regional
        </button>
        <button 
          className={`tab-button ${activeTab === 'global' ? 'active' : ''}`}
          onClick={() => setActiveTab('global')}
        >
          Global
        </button>
      </div>

      <div className="hero-section">
        <h1 className="hero-title">Fixed price,</h1>
        <h1 className="hero-title">No hidden costs, Global</h1>
        <h1 className="hero-title">roaming, Efficient support</h1>
      </div>

      <div className="image-section">
        <div className="hero-image"></div>
      </div>

      <div className="cta-section">
        <button className="cta-button" onClick={() => {
          console.log('See More button clicked');
          onStart();
        }}>See More</button>
      </div>
    </div>
  );
};

export default HomePage;