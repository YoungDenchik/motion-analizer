import axios from 'axios'

const BASE = '/api'

export const api = {
  // ── References ────────────────────────────────────────────────────────────

  listReferences() {
    return axios.get(`${BASE}/references`).then(r => r.data)
  },

  recordReference(name, description, videoFile, overwrite = false) {
    const fd = new FormData()
    fd.append('name', name)
    fd.append('description', description)
    fd.append('overwrite', String(overwrite))
    fd.append('video', videoFile)
    return axios.post(`${BASE}/references/record`, fd).then(r => r.data)
  },

  deleteReference(name) {
    return axios.delete(`${BASE}/references/${encodeURIComponent(name)}`).then(r => r.data)
  },

  // ── Analysis ──────────────────────────────────────────────────────────────

  startAnalysis(exercise, videoFile) {
    const fd = new FormData()
    fd.append('exercise', exercise)
    fd.append('video', videoFile)
    return axios.post(`${BASE}/analyze`, fd).then(r => r.data)
  },

  getStatus(jobId) {
    return axios.get(`${BASE}/status/${jobId}`).then(r => r.data)
  },

  /**
   * Poll until status is "done" or "error".
   * onTick(status) is called on every poll response.
   */
  async pollUntilDone(jobId, onTick, intervalMs = 2000) {
    return new Promise((resolve, reject) => {
      const tick = () => {
        this.getStatus(jobId)
          .then(status => {
            onTick(status)
            if (status.status === 'done')  resolve(status.result)
            else if (status.status === 'error') reject(new Error(status.error || 'Analysis failed'))
            else setTimeout(tick, intervalMs)
          })
          .catch(reject)
      }
      tick()
    })
  },
}
