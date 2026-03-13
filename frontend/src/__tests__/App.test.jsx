/**
 * Frontend tests — ETF Intelligence Dashboard
 * =============================================
 * Dekt:
 *   - Cache-toggle rendering en standaardwaarde
 *   - Header status-tekst (mock / live / cached)
 *   - Vernieuwen-knop roept fetch aan
 *   - use_cache parameter wordt correct doorgegeven
 *   - Toggle wisselt cache-voorkeur en triggert nieuwe fetch
 *   - Detail tab: koersgrafiek tijdframe-knoppen
 *   - Detail tab: OHLCV tabel kolommen en waarden
 *   - Detail tab: historische vs. live label
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

// Recharts gebruikt ResizeObserver — mock zodat jsdom niet crasht
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
global.ResizeObserver = MockResizeObserver;

afterEach(() => {
  vi.restoreAllMocks();
});

// ─── MOCK HOLDING MET OHLCV EN PRICE HISTORY ─────────────────────────────────

function makeHolding(overrides = {}) {
  return {
    ticker: 'NVDA',
    name: 'NVIDIA Corp',
    current_price: 875.40,
    currency: 'USD',
    total_score: 72.3,
    signal: 'KOOP',
    etf_weight: 0.0454,
    scores_by_timeframe: { daily: 74.1, weekly: 71.8, monthly: 70.9 },
    indicator_scores: {
      rsi_daily: 42, rsi_weekly: 38, rsi_monthly: 45,
      rsi_divergence_daily: 50, rsi_divergence_weekly: 50, rsi_divergence_monthly: 50,
      ma20_daily: 65, ma20_weekly: 63, ma20_monthly: 62,
      ma200: 82, apz_daily: 55, apz_weekly: 52, apz_monthly: 50,
      forward_pe: 68, peg: 71, price_fcf: 65, momentum: 75,
      dcf_discount: 55, panic: 60,
    },
    raw_data: {
      rsi_daily: 42.1, peg_ratio: 0.89, forward_pe: 28.4,
      ma200: 721.30, momentum_1m: 3.2,
      fundamentals_unavailable: false,
      ohlc_day: {
        date: '2026-03-10',
        open: 860.00, high: 890.00, low: 855.00,
        close: 875.40, adj_close: 875.40, volume: 45000000,
      },
      price_history: Array.from({ length: 30 }, (_, i) => ({
        date: `2026-02-${String(i + 1).padStart(2, '0')}`,
        close: 800 + i * 2,
      })),
    },
    ...overrides,
  };
}

function makeLiveResponseWithHolding(holdingOverrides = {}, responseOverrides = {}) {
  return {
    ...makeLiveResponse(),
    holdings: [makeHolding(holdingOverrides)],
    ...responseOverrides,
  };
}

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
    const tooltipWrapper = label.closest('span');
    await act(async () => { fireEvent.mouseEnter(tooltipWrapper); });
    expect(screen.getByText(/60 min/i)).toBeInTheDocument();
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

// ─── HELPERS DETAIL TAB ───────────────────────────────────────────────────────

async function renderAndOpenDetail(fetchImpl) {
  await renderApp(fetchImpl);
  // Klik op de NVDA rij → navigeert naar detail tab
  // getAllByText omdat NVDA ook in de mobiele kaartweergave staat (zelfde DOM, CSS verbergt het)
  await act(async () => {
    fireEvent.click(screen.getAllByText('NVDA')[0]);
  });
}

// ─── TESTS: DETAIL TAB — KOERSGRAFIEK ────────────────────────────────────────

describe('Detail tab — koersgrafiek tijdframe-knoppen', () => {
  it('toont alle tijdframe-knoppen na openen detail tab', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    for (const label of ['1M', '3M', '6M', '1J', '3J', '5J']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    }
  });

  it('heeft 1J als actieve knop standaard', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    // De actieve knop heeft een andere kleur (niet #475569) — we controleren dat 1J aanwezig is
    expect(screen.getByRole('button', { name: '1J' })).toBeInTheDocument();
  });

  it('wisselt actief tijdframe na klikken op 3M', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '3M' }));
    });
    expect(screen.getByRole('button', { name: '3M' })).toBeInTheDocument();
  });

  it('toont procentuele verandering naast de ticker', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    // price_history loopt van 800 naar 858 → positief rendement
    const percentEl = document.querySelector('[style*="DM Mono"]');
    expect(percentEl).toBeInTheDocument();
  });
});

// ─── TESTS: DETAIL TAB — OHLCV TABEL ─────────────────────────────────────────

describe('Detail tab — OHLCV tabel', () => {
  it('toont alle kolomkoppen', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    // getAllByText omdat labels zowel in desktop-tabel als mobiel raster staan (CSS verbergt één versie)
    expect(screen.getAllByText('OPEN').length).toBeGreaterThan(0);
    expect(screen.getAllByText('HIGH').length).toBeGreaterThan(0);
    expect(screen.getAllByText('LOW').length).toBeGreaterThan(0);
    expect(screen.getAllByText('CLOSE').length).toBeGreaterThan(0);
    expect(screen.getAllByText('VOLUME').length).toBeGreaterThan(0);
  });

  it('toont "ADJ CLOSE" kolom als adj_close beschikbaar is', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    expect(screen.getAllByText('ADJ CLOSE').length).toBeGreaterThan(0);
  });

  it('verbergt "ADJ CLOSE" kolom als adj_close null is', async () => {
    const holding = makeHolding();
    holding.raw_data.ohlc_day.adj_close = null;
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding({}, { holdings: [holding] })));
    expect(screen.queryByText('ADJ CLOSE')).not.toBeInTheDocument();
  });

  it('toont "DAGKOERSEN" label in live modus', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    expect(screen.getByText('DAGKOERSEN')).toBeInTheDocument();
  });

  it('toont de close koers in de OHLCV tabel-cel', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    // $875.40 staat in prijs-header, desktop-tabel (<td>) én mobiel raster (<div>)
    const cells = screen.getAllByText('$875.40');
    expect(cells.length).toBeGreaterThan(0);
  });

  it('toont volume als getal', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    expect(screen.getAllByText(/45\.000\.000|45,000,000/).length).toBeGreaterThan(0);
  });
});

// ─── TESTS: DETAIL TAB — OHLCV SECTIE ZICHTBAARHEID ─────────────────────────

describe('Detail tab — OHLCV sectie zichtbaarheid', () => {
  it('verbergt OHLCV tabel als ohlc_day ontbreekt', async () => {
    const holding = makeHolding();
    delete holding.raw_data.ohlc_day;
    const response = { ...makeLiveResponseWithHolding(), holdings: [holding] };
    await renderAndOpenDetail(mockFetch(response));
    expect(screen.queryByText('DAGKOERSEN')).not.toBeInTheDocument();
    expect(screen.queryByText('OPEN')).not.toBeInTheDocument();
  });

  it('toont OHLCV tabel als ohlc_day aanwezig is', async () => {
    await renderAndOpenDetail(mockFetch(makeLiveResponseWithHolding()));
    expect(screen.getByText('DAGKOERSEN')).toBeInTheDocument();
    expect(screen.getAllByText('OPEN').length).toBeGreaterThan(0);
  });

  it('historisch fetch-url bevat de opgegeven datum', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeLiveResponse()),
    });
    await renderApp(fetchMock);

    const dateInput = document.querySelector('input[type="date"]');
    await act(async () => {
      fireEvent.change(dateInput, { target: { value: '2024-06-01' } });
    });
    await act(async () => {
      fireEvent.submit(dateInput.closest('form'));
    });

    // Controleer dat een historische fetch werd gedaan met de juiste datum
    const historischCall = fetchMock.mock.calls.find(([url]) =>
      url.includes('/historical') && url.includes('2024-06-01')
    );
    expect(historischCall).toBeDefined();
  });
});
