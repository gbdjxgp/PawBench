import { createRoot } from 'react-dom/client';
import App from './App';

const el = document.getElementById('app');
if (!el) {
  throw new Error('mount target #app missing');
}
createRoot(el).render(<App />);
