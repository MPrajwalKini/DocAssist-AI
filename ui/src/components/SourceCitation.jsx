import { useState } from 'react'

function SourceCitation({ sources }) {
    const [expanded, setExpanded] = useState(null)

    if (!sources || sources.length === 0) return null

    return (
        <div className="sources-container">
            {sources.map((src, i) => (
                <div key={i}>
                    <div
                        className="source-chip"
                        onClick={() => setExpanded(expanded === i ? null : i)}
                    >
                        📄 {src.title || 'Document'}
                        <span className="page-num">p.{src.page_number}</span>
                    </div>
                    {expanded === i && (
                        <div className="source-expanded">
                            <strong>Page {src.page_number}</strong> — {src.title || 'Untitled'}
                            <br />
                            <em>"{src.snippet}"</em>
                        </div>
                    )}
                </div>
            ))}
        </div>
    )
}

export default SourceCitation
