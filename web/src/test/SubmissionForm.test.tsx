import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SubmissionForm } from '../components/SubmissionForm';
import { renderWithProviders } from './testUtils';
import type { SubmissionStage } from '../hooks/useSubmissionFlow';

describe('SubmissionForm', () => {
  it('disables submit button when input is empty', () => {
    const mockFlow = {
      stage: { kind: 'idle' } as SubmissionStage,
      formError: null,
      submit: vi.fn(),
      dismiss: vi.fn(),
    };

    renderWithProviders(<SubmissionForm flow={mockFlow} />);

    const input = screen.getByPlaceholderText(/example\.com/i);
    expect(input).toHaveValue('');

    const button = screen.getByRole('button', { name: /investigate/i });
    expect(button).toBeDisabled();
  });

  it('enables submit button when a valid domain is typed', async () => {
    const user = userEvent.setup();
    const mockFlow = {
      stage: { kind: 'idle' } as SubmissionStage,
      formError: null,
      submit: vi.fn(),
      dismiss: vi.fn(),
    };

    renderWithProviders(<SubmissionForm flow={mockFlow} />);

    const input = screen.getByPlaceholderText(/example\.com/i);
    const button = screen.getByRole('button', { name: /investigate/i });

    await user.type(input, 'example.com');
    expect(button).not.toBeDisabled();
  });

  it('submits trimmed domain when form is submitted', async () => {
    const mockSubmit = vi.fn().mockResolvedValue(undefined);
    const mockFlow = {
      stage: { kind: 'idle' } as SubmissionStage,
      formError: null,
      submit: mockSubmit,
      dismiss: vi.fn(),
    };

    renderWithProviders(<SubmissionForm flow={mockFlow} />);

    const input = screen.getByPlaceholderText(/example\.com/i);
    const button = screen.getByRole('button', { name: /investigate/i });

    fireEvent.change(input, { target: { value: '   evil-corp.com   ' } });
    expect(button).not.toBeDisabled();

    fireEvent.click(button);
    expect(mockSubmit).toHaveBeenCalledWith('evil-corp.com');
  });

  it('renders inline error message when flow has formError', () => {
    const mockFlow = {
      stage: { kind: 'idle' } as SubmissionStage,
      formError: 'Domain is malformed or invalid',
      submit: vi.fn(),
      dismiss: vi.fn(),
    };

    renderWithProviders(<SubmissionForm flow={mockFlow} />);

    expect(screen.getByRole('alert')).toHaveTextContent('Domain is malformed or invalid');
  });

  it('renders RateLimitBanner and disables submit when stage is rate_limited', () => {
    const mockFlow = {
      stage: { kind: 'rate_limited', retryAfter: 30 } as SubmissionStage,
      formError: null,
      submit: vi.fn(),
      dismiss: vi.fn(),
    };

    renderWithProviders(<SubmissionForm flow={mockFlow} />);

    expect(screen.getByRole('alert')).toHaveTextContent(/Rate limit reached/i);
    const button = screen.getByRole('button', { name: /investigate/i });
    expect(button).toBeDisabled();
  });
});
