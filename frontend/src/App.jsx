import { useState } from 'react'
import SheetMusic from './SheetMusic'
import './App.css'
import 'html-midi-player' // Import the MIDI player web components

function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [xmlData, setXmlData] = useState(null) 
  const [midiUrl, setMidiUrl] = useState(null) // State to hold the playable audio URL

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0])
    setStatusMessage('')
    setXmlData(null) 
    setMidiUrl(null) // Clear old audio when a new file is picked
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
        setXmlData(data.xml_data) 
        
        // Convert the backend Base64 string into a playable Data URI
        if (data.midi_data) {
          const base64Midi = `data:audio/midi;base64,${data.midi_data}`
          setMidiUrl(base64Midi)
        }
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
      
      {/* The Interactive Playback UI */}
      {midiUrl && (
        <div style={{ margin: '20px 0', padding: '20px', backgroundColor: '#1e1e1e', borderRadius: '8px', border: '1px solid #444' }}>
          <h3 style={{ marginTop: 0 }}>Listen to AI Transcription</h3>
          <p style={{ fontSize: '14px', color: '#aaa', marginBottom: '15px' }}>
            Compare this synthesized playback with your original audio to check for missing notes or timing errors.
          </p>
          
          {/* The Audio Controls */}
          <midi-player
            src={midiUrl}
            sound-font="https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus"
            style={{ width: '100%', display: 'block', marginBottom: '10px' }}
          ></midi-player>
          
          {/* Wrap the visualizer in a hard, white container */}
          <div style={{ 
            backgroundColor: '#ffffff', 
            padding: '10px', 
            borderRadius: '4px', 
            marginBottom: '30px', 
            overflow: 'hidden',
            border: '1px solid #ccc'
          }}>
            <midi-visualizer 
              type="piano-roll" 
              src={midiUrl}
            ></midi-visualizer>
          </div>
        </div> /* <-- THIS WAS THE MISSING BRACKET! */
      )}

      {xmlData && <SheetMusic xmlData={xmlData} />}
    </div>
  )
}

export default App