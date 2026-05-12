import { Navigate, Route, Routes } from 'react-router-dom';
import { Home } from '@/pages/Home';
import { JobView } from '@/pages/JobView';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/jobs/:jobId" element={<JobView />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
