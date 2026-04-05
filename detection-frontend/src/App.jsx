import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const fetchImages = async () => {
    setLoading(true)
    try {
      let url = 'http://localhost:5000/images'
      const params = new URLSearchParams()
      if (fromDate) params.append('from_date', fromDate)
      if (toDate) params.append('to_date', toDate)
      
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
    fetchImages()
  }, [fromDate, toDate])

  return (
    <div className="gallery-container">
      <header>
        <h1>Person Detections</h1>
        <p className="subtitle">Real-time alerts and captures from your security system</p>
        
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

      <footer>
        <p>© 2026 Antigravity Security Systems</p>
      </footer>
    </div>
  )
}

export default App
