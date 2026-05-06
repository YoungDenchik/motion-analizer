import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Analyze from './pages/Analyze'
import Record from './pages/Record'
import Library from './pages/Library'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/"         element={<Home />} />
        <Route path="/analyze"  element={<Analyze />} />
        <Route path="/record"   element={<Record />} />
        <Route path="/library"  element={<Library />} />
        <Route path="*"         element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
