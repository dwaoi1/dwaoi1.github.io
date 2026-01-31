import { render, screen } from '@testing-library/react';
import App from './App';

test('renders app header', () => {
  render(<App />);
  const header = screen.getByText(/One Piece Card Game Index/i);
  expect(header).toBeInTheDocument();
});
