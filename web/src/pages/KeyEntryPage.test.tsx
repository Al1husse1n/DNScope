import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KeyEntryPage } from './KeyEntryPage';
import { renderWithProviders } from '../test/testUtils';
import * as keysApi from '../api/keys';
import { ApiError } from '../api/client';

vi.mock('../api/keys');

describe('KeyEntryPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it('shows inline error message when API key test fails with 401', async () => {
    vi.mocked(keysApi.testApiKey).mockRejectedValueOnce(new ApiError(401, 'invalid_api_key'));

    renderWithProviders(<KeyEntryPage />, { rawKey: null });

    const input = screen.getByPlaceholderText(/paste your x-api-key/i);
    const submitBtn = screen.getByRole('button', { name: /test & continue/i });

    await userEvent.type(input, 'bad-key-123');
    await userEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/invalid api key\. try again\./i)).toBeInTheDocument();
    });
    expect(localStorage.getItem('dnscope.api_key')).toBeNull();
  });

  it('persists key and navigates upon successful testApiKey verification', async () => {
    vi.mocked(keysApi.testApiKey).mockResolvedValueOnce(undefined);

    renderWithProviders(<KeyEntryPage />, { rawKey: null });

    const input = screen.getByPlaceholderText(/paste your x-api-key/i);
    const submitBtn = screen.getByRole('button', { name: /test & continue/i });

    await userEvent.type(input, 'valid-secret-key-123');
    await userEvent.click(submitBtn);

    await waitFor(() => {
      expect(keysApi.testApiKey).toHaveBeenCalledWith('valid-secret-key-123');
    });
  });
});
