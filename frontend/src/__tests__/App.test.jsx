/**
 * Frontend tests — ETF Intelligence Dashboard
 * =============================================
 * Dekt:
 *   - Cache-toggle rendering en standaardwaarde
 *   - Header status-tekst (mock / live / cached)
 *   - Vernieuwen-knop roept fetch aan
 *   - use_cache parameter wordt correct doorgegeven
 *   - Toggle wisselt cache-voorkeur en triggert nieuwe fetch
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { vi, describe, it, expect, afterEach } from 'vitest';
import App from '../App';

// ─── MOCK fetch ───────────────────────────────────────────────────────────────

const makeLiveResponse = (cached = false, cacheAgeMinutes = 0) => ({
  summary: { etf_score: 61.4, etf_signal: 'AFWACHTEN', holdings_analyzed: 10, holdings_total: 10 },
  generated_at: new Date('2026-03-10T12:00:00').toISOString(),
  cached,
  cache_age_minutes: cacheAgeMinutes,
  config: {
    timeframe_weights: { daily: 0.30, weekly: 0.40, monthly: 0.30 },
    indicator_weights: {
      rsi: 0.13, ma20: 0.08, ma200: 0.07, forward_pe: 0.15,
      peg: 0.15, price_fcf: 0.11, momentum: 0.08,
      dcf_discount: 0.02, panic: 0.05, rsi_divergence: 0.08, apz: 0.08,
    },
  },
  holdings: [],
});

function mockFetch(responseData) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(responseData),
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── HELPERS ──────────────────────────────────────────────────────────────────

async function renderApp(fetchImpl) {
  global.fetch = fetchImpl;
  let result;
  await act(async () => {
    result = render(<App />);
  });
  return result;
}

// ─── TESTS ────────────────────────────────────────────────────────────────────

describe('Cache toggle', () => {
  it('wordt gerenderd in de header', async () => {
    await renderApp(mockFetch(makeLiveResponse()));
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
  });

  it('is standaard aangevinkt (cache aan)', async () => {
    await renderApp(mockFetch(makeLiveResponse()));
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  it('heeft het label "Cache"', async () => {
    await renderApp(mockFetch(makeLiveResponse()));
    expect(screen.getByText(/Cache/i)).toBeInTheDocument();
  });

  it('heeft een tooltip met uitleg over 60 minuten', async () => {
    await renderApp(mockFetch(makeLiveResponse()));
    const label = screen.getByText(/Cache/i).closest('label');
    expect(label).toHaveAttribute('title');
    expect(label.getAttribute('title')).toMatch(/60 min/);
  });
});

describe('use_cache parameter in fetch-aanroep', () => {
  it('stuurt use_cache=true mee bij initieel laden (standaard aan)', async () => {
    const fetchMock = mockFetch(makeLiveResponse());
    await renderApp(fetchMock);
    expect(fetchMock).toHaveBeenCalled();
    expect(fetchMock.mock.calls[0][0]).toMatch(/use_cache=true/);
  });

  it('stuurt use_cache=false mee na uitvinken toggle', async () => {
    const fetchMock = mockFetch(makeLiveResponse());
    await renderApp(fetchMock);

    await act(async () => {
      fireEvent.click(screen.getByRole('checkbox'));
    });

    // Toggle onChange roept fetchLiveData(false) aan + useEffect re-runt:
    // alle calls na de eerste moeten use_cache=false hebben
    const callsAfterToggle = fetchMock.mock.calls.slice(1);
    expect(callsAfterToggle.length).toBeGreaterThan(0);
    expect(callsAfterToggle.every(c => c[0].includes('use_cache=false'))).toBe(true);
  });

  it('stuurt use_cache=true mee na opnieuw aanvinken', async () => {
    const fetchMock = mockFetch(makeLiveResponse());
    await renderApp(fetchMock);

    await act(async () => { fireEvent.click(screen.getByRole('checkbox')); }); // uit
    const callsAfterUit = fetchMock.mock.calls.length;

    await act(async () => { fireEvent.click(screen.getByRole('checkbox')); }); // aan

    const callsAfterAan = fetchMock.mock.calls.slice(callsAfterUit);
    expect(callsAfterAan.length).toBeGreaterThan(0);
    expect(callsAfterAan.every(c => c[0].includes('use_cache=true'))).toBe(true);
  });
});

describe('Vernieuwen knop', () => {
  it('triggert een nieuwe fetch bij klikken', async () => {
    const fetchMock = mockFetch(makeLiveResponse());
    await renderApp(fetchMock);

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Vernieuwen/i }));
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('toont de knoptekst "Vernieuwen"', async () => {
    await renderApp(mockFetch(makeLiveResponse()));
    expect(screen.getByRole('button', { name: /Vernieuwen/i })).toBeInTheDocument();
  });
});

describe('Header status tekst', () => {
  it('toont mock-waarschuwing als fetch mislukt', async () => {
    const failFetch = vi.fn().mockRejectedValue(new Error('Network error'));
    await renderApp(failFetch);
    // Zoek specifiek in de header-subtitle (DM Mono, klein lettertype)
    const statusEl = document.querySelector('[style*="DM Mono"][style*="font-size: 11px"]');
    expect(statusEl?.textContent).toMatch(/Mock data/i);
  });

  it('toont "Live" als data niet gecached is', async () => {
    await renderApp(mockFetch(makeLiveResponse(false)));
    const statusEl = document.querySelector('[style*="DM Mono"][style*="font-size: 11px"]');
    expect(statusEl?.textContent).toMatch(/Live/i);
  });

  it('toont "uit cache" als data gecached is', async () => {
    await renderApp(mockFetch(makeLiveResponse(true, 12)));
    expect(screen.getByText(/uit cache/i)).toBeInTheDocument();
  });

  it('toont cache-leeftijd in minuten', async () => {
    await renderApp(mockFetch(makeLiveResponse(true, 12)));
    expect(screen.getByText(/12 min geleden/i)).toBeInTheDocument();
  });
});
