import React, { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  Download,
  Edit3,
  FileText,
  Files,
  HelpCircle,
  Loader2,
  Play,
  Settings2,
  Table,
  UploadCloud,
} from 'lucide-react'

const toolLabels = {
  extract_schema_tool: 'Đọc cấu trúc biểu mẫu',
  read_and_clean_raw_tool: 'Đọc và bảo vệ dữ liệu tài liệu',
  extract_kpis_tool: 'Trích xuất số liệu báo cáo',
  validate_and_correct_tool: 'Đối chiếu và kiểm tra số liệu',
  generate_section_remarks_tool: 'Soạn nội dung nhận xét',
  render_docx_report_tool: 'Hoàn thiện báo cáo Word',
}

function App() {
  const [templateFile, setTemplateFile] = useState(null)
  const [rawFiles, setRawFiles] = useState([])
  const [apiKey, setApiKey] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [statusText, setStatusText] = useState('Sẵn sàng xử lý')
  const [statusType, setStatusType] = useState('idle')
  const [logs, setLogs] = useState([])
  const [sessionId, setSessionId] = useState('')
  const [kpiData, setKpiData] = useState({})
  const [remarks, setRemarks] = useState('')
  const [isCompleted, setIsCompleted] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const progressRef = useRef(null)

  useEffect(() => {
    if (progressRef.current) progressRef.current.scrollTop = progressRef.current.scrollHeight
  }, [logs])

  const appendLog = (type, message) => setLogs((prev) => [...prev, { type, message }])

  const handleRun = async () => {
    if (!templateFile) {
      window.alert('Vui lòng chọn biểu mẫu báo cáo trước khi phân tích.')
      return
    }
    if (rawFiles.length === 0) {
      window.alert('Vui lòng chọn ít nhất một báo cáo của phòng ban.')
      return
    }

    setLogs([])
    setKpiData({})
    setRemarks('')
    setIsCompleted(false)
    setIsRunning(true)
    setStatusText('Đang tải tài liệu lên hệ thống')
    setStatusType('running')

    const formData = new FormData()
    formData.append('template', templateFile)
    rawFiles.forEach((file) => formData.append('raws', file))
    if (apiKey.trim()) formData.append('fpt_api_key', apiKey.trim())

    try {
      appendLog('info', `Đã tiếp nhận ${rawFiles.length + 1} tệp. Bắt đầu xử lý.`)
      const response = await fetch('/api/agent/run', { method: 'POST', body: formData })
      if (!response.ok) throw new Error(`Máy chủ phản hồi mã ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop()
        for (const event of events) {
          if (!event.startsWith('data: ')) continue
          try {
            handleEvent(JSON.parse(event.slice(6)))
          } catch (error) {
            console.error('Không đọc được dữ liệu tiến trình:', error)
          }
        }
      }
    } catch (error) {
      appendLog('error', `Không thể hoàn tất xử lý: ${error.message}`)
      setStatusText('Xử lý chưa thành công')
      setStatusType('error')
      setIsRunning(false)
    }
  }

  const handleEvent = (data) => {
    if (data.status === 'init') {
      setSessionId(data.session_id)
      setStatusText('Đang đọc và phân tích tài liệu')
      return
    }
    if (data.status === 'running') {
      if (data.action && data.action !== 'Không rõ') {
        appendLog('action', toolLabels[data.action] || 'Đang xử lý dữ liệu')
      } else if (data.observation) {
        appendLog('info', data.observation)
      }
      return
    }
    if (data.status === 'completed') {
      appendLog('complete', 'Đã phân tích xong. Vui lòng kiểm tra số liệu và nội dung nhận xét.')
      setStatusText('Đã hoàn tất phân tích')
      setStatusType('success')
      setIsRunning(false)
      setIsCompleted(true)
      if (data.final_answer?.kpi_data) setKpiData(data.final_answer.kpi_data)
      if (data.final_answer?.combined_remarks) setRemarks(data.final_answer.combined_remarks)
      setTimeout(() => document.getElementById('review')?.scrollIntoView({ behavior: 'smooth' }), 100)
      return
    }
    if (data.status === 'error') {
      appendLog('error', data.message || 'Hệ thống gặp lỗi khi xử lý tài liệu.')
      setStatusText('Xử lý chưa thành công')
      setStatusType('error')
      setIsRunning(false)
    }
  }

  const handleKpiChange = (key, value) => {
    setKpiData((prev) => ({ ...prev, [key]: value === '' ? null : isNaN(value) ? value : Number(value) }))
  }

  const handleDownload = async () => {
    if (!sessionId) return
    setIsDownloading(true)
    try {
      const response = await axios.post('/api/agent/render-docx', {
        session_id: sessionId,
        kpi_data: kpiData,
        remarks,
      }, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.download = `Bao_cao_tong_hop_${sessionId.slice(0, 8)}.docx`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      appendLog('complete', 'Đã tạo và tải báo cáo Word về máy.')
    } catch (error) {
      console.error(error)
      window.alert('Không thể tạo tệp báo cáo. Vui lòng thử lại.')
    } finally {
      setIsDownloading(false)
    }
  }

  const friendlyKpiName = (key) => {
    let label = key.replaceAll('_', ' ')
    if (key.includes('tong_thu_ngan_sach')) label = 'Thu ngân sách nhà nước'
    else if (key.includes('tong_chi_ngan_sach')) label = 'Chi ngân sách địa phương'
    else if (key.includes('dang_ky_khai_sinh')) label = 'Hồ sơ khai sinh'
    else if (key.includes('dang_ky_khai_tu')) label = 'Hồ sơ khai tử'
    else if (key.includes('tam_tru_moi')) label = 'Hồ sơ đăng ký tạm trú'
    else if (key.includes('chung_thuc_chu_ky')) label = 'Hồ sơ chứng thực chữ ký'
    else if (key.includes('vi_pham_an_ninh_trat_tu')) label = 'Số vụ vi phạm an ninh trật tự'
    if (key.endsWith('_ky_truoc')) return `${label} (kỳ trước)`
    if (key.endsWith('_ky_bao_cao')) return `${label} (kỳ báo cáo)`
    return label.charAt(0).toUpperCase() + label.slice(1)
  }

  const hasFiles = templateFile && rawFiles.length > 0

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-mark"><ClipboardCheck aria-hidden="true" /></div>
            <div>
              <h1>Trợ lý tổng hợp báo cáo</h1>
              <p>Hỗ trợ tổng hợp số liệu, kiểm tra nội dung và hoàn thiện báo cáo định kỳ</p>
            </div>
          </div>
          <div className={`system-status ${statusType}`}>
            <span className="status-dot" />
            {statusType === 'running' ? 'Hệ thống đang xử lý' : 'Hệ thống sẵn sàng'}
          </div>
        </div>
      </header>

      <main className="page-container">
        <section className="welcome-row">
          <div>
            <p className="eyebrow">TỔNG HỢP BÁO CÁO ĐỊNH KỲ</p>
            <h2>Hoàn thiện báo cáo qua 3 bước</h2>
            <p>Tải tài liệu, để AI hỗ trợ phân tích, sau đó kiểm tra trước khi xuất báo cáo.</p>
          </div>
          <button className="settings-toggle" onClick={() => setShowSettings(!showSettings)}>
            <Settings2 /> Tùy chọn hệ thống <ChevronDown className={showSettings ? 'rotate' : ''} />
          </button>
        </section>

        {showSettings && (
          <section className="settings-panel">
            <div>
              <h3>Cấu hình kết nối</h3>
              <p>Chỉ dành cho cán bộ quản trị. Người dùng thông thường có thể bỏ qua mục này.</p>
            </div>
            <label>
              Khóa kết nối FPT AI (không bắt buộc)
              <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="Hệ thống sẽ dùng cấu hình có sẵn nếu để trống" />
            </label>
          </section>
        )}

        <nav className="stepper" aria-label="Tiến trình thực hiện">
          <div className="step active"><span>1</span><div><strong>Chọn tài liệu</strong><small>Biểu mẫu và báo cáo nguồn</small></div></div>
          <ChevronRight />
          <div className={`step ${isRunning || isCompleted ? 'active' : ''}`}><span>2</span><div><strong>Phân tích</strong><small>Trích xuất và kiểm tra số liệu</small></div></div>
          <ChevronRight />
          <div className={`step ${isCompleted ? 'active' : ''}`}><span>3</span><div><strong>Kiểm tra và xuất</strong><small>Hoàn thiện báo cáo Word</small></div></div>
        </nav>

        <section className="card">
          <div className="section-heading">
            <div className="section-number">1</div>
            <div><h2>Chọn tài liệu</h2><p>Tải lên biểu mẫu cần điền và các báo cáo nguồn của phòng ban.</p></div>
          </div>
          <div className="upload-grid">
            <label className={`upload-box ${templateFile ? 'selected' : ''}`}>
              <input type="file" accept=".docx" onChange={(e) => setTemplateFile(e.target.files?.[0] || null)} />
              <div className="upload-icon"><FileText /></div>
              <strong>{templateFile ? 'Đã chọn biểu mẫu' : 'Biểu mẫu báo cáo'}</strong>
              <span>{templateFile?.name || 'Tệp Word (.docx) cần được hoàn thiện'}</span>
              <em><UploadCloud /> {templateFile ? 'Chọn tệp khác' : 'Chọn tệp từ máy tính'}</em>
            </label>
            <label className={`upload-box ${rawFiles.length ? 'selected' : ''}`}>
              <input type="file" multiple accept=".docx,.xlsx,.pdf,.png,.jpg,.jpeg" onChange={(e) => setRawFiles(Array.from(e.target.files || []))} />
              <div className="upload-icon"><Files /></div>
              <strong>{rawFiles.length ? `Đã chọn ${rawFiles.length} báo cáo` : 'Báo cáo của các phòng ban'}</strong>
              <span>{rawFiles.length ? rawFiles.map((file) => file.name).join(', ') : 'Hỗ trợ Word, Excel, PDF và ảnh scan'}</span>
              <em><UploadCloud /> {rawFiles.length ? 'Chọn lại danh sách' : 'Chọn một hoặc nhiều tệp'}</em>
            </label>
          </div>
        </section>

        <section className="card">
          <div className="section-heading action-heading">
            <div className="heading-copy"><div className="section-number">2</div><div><h2>Phân tích và kiểm tra số liệu</h2><p>AI sẽ đọc tài liệu, tổng hợp chỉ tiêu và phát hiện nội dung cần kiểm tra.</p></div></div>
            <button className="primary-button" onClick={handleRun} disabled={isRunning || !hasFiles}>
              {isRunning ? <Loader2 className="spin" /> : <Play />} {isRunning ? 'Đang phân tích...' : 'Phân tích báo cáo'}
            </button>
          </div>

          <div className={`progress-panel ${statusType}`}>
            <div className="progress-header">
              <div>{statusType === 'error' ? <AlertCircle /> : <CheckCircle2 />}<strong>Tiến trình xử lý</strong></div>
              <span>{statusText}</span>
            </div>
            <div className="progress-list" ref={progressRef}>
              {logs.length === 0 ? (
                <div className="empty-state"><HelpCircle /><p>Chọn đầy đủ tài liệu rồi nhấn <strong>Phân tích báo cáo</strong> để bắt đầu.</p></div>
              ) : logs.map((log, index) => (
                <div className={`progress-item ${log.type}`} key={`${index}-${log.message}`}>
                  <span>{log.type === 'error' ? '!' : log.type === 'complete' ? '✓' : index + 1}</span>
                  <p>{log.message}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="review" className={`card review-card ${isCompleted ? '' : 'disabled'}`}>
          <div className="section-heading action-heading">
            <div className="heading-copy"><div className="section-number">3</div><div><h2>Kiểm tra và xuất báo cáo</h2><p>Rà soát số liệu và nội dung nhận xét trước khi tải báo cáo.</p></div></div>
            <button className="success-button" onClick={handleDownload} disabled={isDownloading || !sessionId}>
              {isDownloading ? <Loader2 className="spin" /> : <Download />} {isDownloading ? 'Đang tạo báo cáo...' : 'Tải báo cáo Word'}
            </button>
          </div>
          {!isCompleted ? (
            <div className="locked-message"><ClipboardCheck /><p>Kết quả sẽ hiển thị tại đây sau khi hệ thống phân tích xong.</p></div>
          ) : (
            <div className="review-grid">
              <div className="review-panel">
                <h3><Table /> Số liệu tổng hợp</h3>
                <p className="field-help">Có thể chỉnh sửa trực tiếp các giá trị chưa chính xác.</p>
                <div className="data-list">
                  {Object.keys(kpiData).length === 0 ? <p className="muted">Không tìm thấy số liệu phù hợp.</p> : Object.entries(kpiData).map(([key, value]) => (
                    <label className="data-row" key={key}>
                      <span title={key}>{friendlyKpiName(key)}</span>
                      <input value={value ?? ''} onChange={(e) => handleKpiChange(key, e.target.value)} />
                    </label>
                  ))}
                </div>
              </div>
              <div className="review-panel">
                <h3><Edit3 /> Nội dung nhận xét</h3>
                <p className="field-help">Kiểm tra và điều chỉnh cách diễn đạt nếu cần.</p>
                <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} placeholder="Nội dung nhận xét sẽ hiển thị tại đây." />
              </div>
            </div>
          )}
        </section>
      </main>

      <footer>Hệ thống hỗ trợ tổng hợp báo cáo • Dữ liệu cần được cán bộ phụ trách kiểm tra trước khi ban hành</footer>
    </div>
  )
}

export default App
