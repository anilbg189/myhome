import { useState, useEffect } from 'react'
import { PushNotifications } from '@capacitor/push-notifications'
import './App.css'

const API_BASE_URL = 'https://myhome-7rfa.onrender.com'

function App() {
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [detectionEnabled, setDetectionEnabled] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 20

  useEffect(() => {
    // Request permission to use push notifications
    // iOS will prompt user and return if they granted permission or not
    // Android will return 'granted' without prompting user
    PushNotifications.requestPermissions().then(result => {
      if (result.receive === 'granted') {
        // Register with Apple / Google to receive push via APNS/FCM
        PushNotifications.register();
      } else {
        // Show some error
        console.error("Push registration failed: Permission denied");
      }
    });

    // On success, we should be able to receive notifications
    PushNotifications.addListener('registration', (token) => {
      console.log('Push registration success, token: ' + token.value);
      // Send the token to the backend
      fetch(`${API_BASE_URL}/register-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token.value })
      }).catch(err => console.error('Error sending token to backend:', err));
    });

    // Some issue with our setup and push will not work
    PushNotifications.addListener('registrationError', (error) => {
      console.error('Error on registration: ' + JSON.stringify(error));
    });

    // Show us the notification payload if the app is open on our device
    PushNotifications.addListener('pushNotificationReceived', (notification) => {
      console.log('Push received: ' + JSON.stringify(notification));
    });

    // Method called when tapping on a notification
    PushNotifications.addListener('pushNotificationActionPerformed', (notification) => {
      console.log('Push action performed: ' + JSON.stringify(notification));
    });

    return () => {
      PushNotifications.removeAllListeners();
    };
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/status`)
      if (response.ok) {
        const data = await response.json()
        setDetectionEnabled(data.detection_enabled)
      }
    } catch (err) {
      console.error('Error fetching status:', err)
    }
  }

  const toggleDetection = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/toggle-detection`, {
        method: 'POST'
      })
      if (response.ok) {
        const data = await response.json()
        setDetectionEnabled(data.detection_enabled)
      } else {
        throw new Error('Failed to toggle detection')
      }
    } catch (err) {
      console.error('Error toggling detection:', err)
      alert('Failed to update detection status')
    }
  }

  const fetchImages = async () => {
    setLoading(true)
    try {
      let url = `${API_BASE_URL}/images`
      const params = new URLSearchParams()
      if (fromDate) params.append('from_date', fromDate)
      if (toDate) params.append('to_date', toDate)
      
      params.append('skip', (currentPage - 1) * itemsPerPage)
      params.append('limit', itemsPerPage)

      if (params.toString()) {
        url += `?${params.toString()}`
      }

      const response = await fetch(url)
      if (!response.ok) {
        throw new Error('Failed to fetch images')
      }
      const data = await response.json()
      setImages(data)
      setError(null)
    } catch (err) {
      console.error('Error fetching images:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const clearFilters = () => {
    setFromDate('')
    setToDate('')
  }

  useEffect(() => {
    setCurrentPage(1)
  }, [fromDate, toDate])

  useEffect(() => {
    fetchStatus()
    fetchImages()
  }, [fromDate, toDate, currentPage])

  return (
    <div className="gallery-container">
      <header>
        <div className="header-main">
          <div>
            <h1>Person Detections</h1>
            <p className="subtitle">Real-time alerts and captures from your security system</p>
          </div>
          <div className="detection-control">
            <button 
              className={`toggle-btn ${detectionEnabled ? 'active' : 'inactive'}`} 
              onClick={toggleDetection}
            >
              {detectionEnabled ? '● Detection Active' : '○ Detection Paused'}
            </button>
          </div>
        </div>
        
        <div className="filter-bar">
          <div className="filter-group">
            <label>From:</label>
            <input 
              type="date" 
              value={fromDate} 
              onChange={(e) => setFromDate(e.target.value)} 
            />
          </div>
          <div className="filter-group">
            <label>To:</label>
            <input 
              type="date" 
              value={toDate} 
              onChange={(e) => setToDate(e.target.value)} 
            />
          </div>
          <button className="clear-btn" onClick={clearFilters} disabled={!fromDate && !toDate}>
            Clear Filters
          </button>
          <button className="refresh-btn" onClick={fetchImages}>
            ↻ Refresh
          </button>
        </div>
      </header>

      {loading ? (
        <div className="loading-container">
          <span className="loader"></span>
        </div>
      ) : error ? (
        <div className="error-state">
          <p>Error: {error}</p>
          <button className="refresh-btn" onClick={fetchImages}>Try Again</button>
        </div>
      ) : images.length === 0 ? (
        <div className="empty-state">
          <p>No detections found yet. Keep an eye out!</p>
        </div>
      ) : (
        <div className="grid">
          {images.map((img) => (
            <div key={img.file_id} className="card">
              <div className="image-wrapper">
                <img src={img.url} alt={img.name} loading="lazy" />
              </div>
              <div className="card-content">
                <div className="card-title">{img.name}</div>
                <div className="card-date">
                  {new Date(img.created_at).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short'
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="pagination">
        <button 
          className="pagination-btn" 
          onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
          disabled={currentPage === 1 || loading}
        >
          Previous
        </button>
        <span className="page-info">Page {currentPage}</span>
        <button 
          className="pagination-btn" 
          onClick={() => setCurrentPage(prev => prev + 1)}
          disabled={images.length < itemsPerPage || loading}
        >
          Next
        </button>
      </div>

      <footer>
        <p>© 2026 Antigravity Security Systems</p>
      </footer>
    </div>
  )
}

export default App
