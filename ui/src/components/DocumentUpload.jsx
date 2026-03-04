import { useState, useRef } from 'react'

function DocumentUpload({ onUploadComplete }) {
    const [uploading, setUploading] = useState(false)
    const [progress, setProgress] = useState(0)
    const [dragover, setDragover] = useState(false)
    const [result, setResult] = useState(null)
    const fileRef = useRef(null)

    const handleUpload = async (file) => {
        if (!file) return
        setUploading(true)
        setProgress(30)
        setResult(null)

        const formData = new FormData()
        formData.append('file', file)

        try {
            setProgress(60)
            const res = await fetch('/api/documents/upload', {
                method: 'POST',
                body: formData,
            })

            setProgress(90)

            if (!res.ok) {
                const err = await res.json()
                throw new Error(err.detail || 'Upload failed')
            }

            const data = await res.json()
            setProgress(100)
            setResult({ success: true, ...data })
            onUploadComplete?.()

            setTimeout(() => {
                setUploading(false)
                setProgress(0)
                setResult(null)
            }, 3000)
        } catch (e) {
            setResult({ success: false, error: e.message })
            setUploading(false)
            setProgress(0)
        }
    }

    const onDrop = (e) => {
        e.preventDefault()
        setDragover(false)
        const file = e.dataTransfer.files[0]
        if (file) handleUpload(file)
    }

    return (
        <>
            <div
                className={`upload-zone ${dragover ? 'dragover' : ''}`}
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragover(true) }}
                onDragLeave={() => setDragover(false)}
                onDrop={onDrop}
            >
                <div className="upload-icon">📁</div>
                <div>Drop a document here or click to upload</div>
                <div style={{ fontSize: 12, marginTop: 4, color: 'var(--text-muted)' }}>
                    PDF, DOCX, TXT, Markdown, HTML
                </div>
                <input
                    ref={fileRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.md,.markdown,.html,.htm"
                    style={{ display: 'none' }}
                    onChange={(e) => handleUpload(e.target.files[0])}
                />
            </div>

            {uploading && (
                <div className="upload-progress">
                    <span className="status-dot processing" />
                    <div className="progress-bar">
                        <div className="fill" style={{ width: `${progress}%` }} />
                    </div>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{progress}%</span>
                </div>
            )}

            {result && (
                <div className="upload-progress" style={{
                    borderLeft: `3px solid ${result.success ? 'var(--success)' : 'var(--error)'}`,
                }}>
                    {result.success ? (
                        <span style={{ fontSize: 13 }}>
                            Indexed <strong>{result.filename}</strong> — {result.total_pages} pages
                        </span>
                    ) : (
                        <span style={{ fontSize: 13, color: 'var(--error)' }}>
                            {result.error}
                        </span>
                    )}
                </div>
            )}
        </>
    )
}

export default DocumentUpload
