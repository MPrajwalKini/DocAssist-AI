import { useState, useRef, useEffect } from 'react'
import SourceCitation from './SourceCitation'

function ChatInterface({ messages, onSend }) {
    const [input, setInput] = useState('')
    const [sending, setSending] = useState(false)
    const messagesEndRef = useRef(null)
    const textareaRef = useRef(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const handleSend = async () => {
        if (!input.trim() || sending) return
        setSending(true)
        const msg = input.trim()
        setInput('')
        if (textareaRef.current) textareaRef.current.style.height = '52px'
        await onSend(msg)
        setSending(false)
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    const handleInput = (e) => {
        setInput(e.target.value)
        // Auto-resize textarea
        e.target.style.height = '52px'
        e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
    }

    const hasMessages = messages.length > 0

    return (
        <>
            {hasMessages ? (
                <div className="chat-messages">
                    {messages.map((msg, i) => (
                        <div key={i} className={`message message-${msg.role}`}>
                            <div className="message-bubble">
                                {msg.loading ? (
                                    <div className="loading-dots">
                                        <span /><span /><span />
                                    </div>
                                ) : (
                                    <>
                                        {msg.content.split('\n').map((line, j) => (
                                            <p key={j}>{line || '\u00A0'}</p>
                                        ))}
                                        {msg.sources_json && (
                                            <SourceCitation sources={JSON.parse(msg.sources_json)} />
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    ))}
                    <div ref={messagesEndRef} />
                </div>
            ) : (
                <div className="empty-state">
                    <div className="logo">◆</div>
                    <h2>Document Assistant</h2>
                    <p>Upload documents and ask questions. I'll find relevant passages and provide grounded answers with citations.</p>
                </div>
            )}

            <div className="input-container">
                <div className="input-wrapper">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={handleInput}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask a question about your documents..."
                        rows={1}
                    />
                    <button
                        className="send-btn"
                        onClick={handleSend}
                        disabled={!input.trim() || sending}
                        title="Send message"
                    >
                        ▲
                    </button>
                </div>
            </div>
        </>
    )
}

export default ChatInterface
