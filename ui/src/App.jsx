import { useState, useEffect } from 'react'
import ChatInterface from './components/ChatInterface'
import Sidebar from './components/Sidebar'
import DocumentUpload from './components/DocumentUpload'
import './index.css'

function App() {
  const [conversationId, setConversationId] = useState(null)
  const [conversations, setConversations] = useState([])
  const [documents, setDocuments] = useState([])
  const [messages, setMessages] = useState([])

  const fetchConversations = async () => {
    try {
      const res = await fetch('/api/conversations')
      if (res.ok) setConversations(await res.json())
    } catch (e) { console.error('Failed to fetch conversations:', e) }
  }

  const fetchDocuments = async () => {
    try {
      const res = await fetch('/api/documents')
      if (res.ok) setDocuments(await res.json())
    } catch (e) { console.error('Failed to fetch documents:', e) }
  }

  useEffect(() => {
    fetchConversations()
    fetchDocuments()
  }, [])

  const handleNewChat = () => {
    setConversationId(null)
    setMessages([])
  }

  const handleSelectConversation = async (id) => {
    setConversationId(id)
    try {
      const res = await fetch(`/api/conversations/${id}`)
      if (res.ok) setMessages(await res.json())
    } catch (e) { console.error('Failed to load conversation:', e) }
  }

  const handleSendMessage = async (message) => {
    const userMsg = { role: 'user', content: message, sources_json: null }
    setMessages(prev => [...prev, userMsg])

    // Add loading placeholder
    setMessages(prev => [...prev, { role: 'assistant', content: '', loading: true }])

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, conversation_id: conversationId }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const data = await res.json()
      setConversationId(data.conversation_id)

      // Replace loading with actual response
      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: 'assistant',
          content: data.answer,
          sources_json: data.sources?.length ? JSON.stringify(data.sources) : null,
        },
      ])

      fetchConversations()
    } catch (e) {
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: `Error: ${e.message}. Is the backend running?` },
      ])
    }
  }

  const handleUploadComplete = () => {
    fetchDocuments()
  }

  return (
    <div className="app-container">
      <Sidebar
        conversations={conversations}
        documents={documents}
        activeId={conversationId}
        onNewChat={handleNewChat}
        onSelect={handleSelectConversation}
      />
      <div className="main-content">
        <DocumentUpload onUploadComplete={handleUploadComplete} />
        <ChatInterface messages={messages} onSend={handleSendMessage} />
      </div>
    </div>
  )
}

export default App
