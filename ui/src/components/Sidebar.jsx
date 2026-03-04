function Sidebar({ conversations, documents, activeId, onNewChat, onSelect }) {
    return (
        <aside className="sidebar">
            <div className="sidebar-header">
                <h1>◆ DocAssist AI</h1>
                <button className="new-chat-btn" onClick={onNewChat}>
                    + New Chat
                </button>
            </div>

            <div className="conversation-list">
                {/* Conversations */}
                <div className="sidebar-section-title">Conversations</div>
                {conversations.length === 0 ? (
                    <div className="conversation-item" style={{ color: 'var(--text-muted)', cursor: 'default' }}>
                        No conversations yet
                    </div>
                ) : (
                    conversations.map((c) => (
                        <div
                            key={c.id}
                            className={`conversation-item ${c.id === activeId ? 'active' : ''}`}
                            onClick={() => onSelect(c.id)}
                        >
                            {c.title || 'Untitled'}
                        </div>
                    ))
                )}

                {/* Documents */}
                <div className="sidebar-section-title" style={{ marginTop: 20 }}>Documents</div>
                {documents.length === 0 ? (
                    <div className="doc-item" style={{ color: 'var(--text-muted)' }}>
                        No documents uploaded
                    </div>
                ) : (
                    documents.map((d) => (
                        <div key={d.id} className="doc-item">
                            <span className="doc-icon">📄</span>
                            <span className="doc-name">{d.filename}</span>
                            <span className="doc-pages">{d.total_pages}p</span>
                        </div>
                    ))
                )}
            </div>
        </aside>
    )
}

export default Sidebar
