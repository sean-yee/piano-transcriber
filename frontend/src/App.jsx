import { useState } from 'react'
import SheetMusic from './SheetMusic'
import './App.css'

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [xmlData, setXmlData] = useState(null) // NEW: State to hold the sheet music data

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0])
    setStatusMessage('')
    setXmlData(null) // Clear old sheet music when a new file is picked
  }

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsLoading(true)
    setStatusMessage('Sending to AI for transcription (this takes a moment)...')

    const formData = new FormData()
    formData.append('file', selectedFile)

    try {
      const response = await fetch('http://localhost:8000/transcribe', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.status === 'success') {
        setStatusMessage('Success! Rendering sheet music...')
        setXmlData(data.xml_data) // NEW: Save the XML string to state
      } else {
        setStatusMessage(`Error: ${data.message}`)
      }
    } catch (error) {
      setStatusMessage('Failed to connect to the server.')
      console.error(error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container">
      <h1>AI Piano Transcriber</h1>
      <p>Upload a piano audio file (.wav or .mp3) to generate sheet music.</p>
      
      <div className="upload-section">
        <input type="file" accept="audio/*" onChange={handleFileChange} />
        <button onClick={handleUpload} disabled={isLoading || !selectedFile}>
          {isLoading ? 'Processing...' : 'Transcribe Audio'}
        </button>
      </div>

      {statusMessage && <div className="status-message">{statusMessage}</div>}
      
      {/* NEW: If we have XML data, render the SheetMusic component! */}
      {xmlData && <SheetMusic xmlData={xmlData} />}
    </div>
  )
}

export default App