/**
 * PM2.5 summary values, transcribed from outputs/summary_statistics.txt (section 4)
 * and the bar labels of charts/figure2_pm25_distribution.png (panel C).
 * Raw daily AQS records are not part of the repository outputs, so the daily
 * time series is shown through the original figure rather than re-plotted.
 */
export const BENCHMARKS = {
  whoAnnual: 5.0,
  naaqsAnnual: 9.0,
  whoDaily: 15.0,
  naaqsDaily: 35.0,
};

export const PM_ALL = {
  siteDays: 705,
  period: "1 Jan \u2013 31 Dec 2025",
  mean: 5.65,
  median: 4.5,
  sd: 4.39,
  p95: 13.5,
  p98: 18.2,
  max: 33.5,
  maxDate: "Aug 5, 2025",
  maxSite: "Uxbridge",
  maxAqi: 96,
  daysOverWho: 23,
  distinctDatesOverWho: 14,
  daysOverNaaqs: 0,
  agreementRho: 0.95,
  monitorDistanceKm: 23,
};

export const MONITORS = [
  { name: "Worcester Summer Street", days: 358, mean: 5.75, annualQ: 5.76, p98: 17.93, max: 32.9, overWho: 12, shareOverWho: 3.4 },
  { name: "Uxbridge", days: 347, mean: 5.54, annualQ: 5.49, p98: 18.67, max: 33.5, overWho: 11, shareOverWho: 3.2 },
];

/** Days above each daily-mean threshold (Figure 2C). */
export const EXCEEDANCES = [
  { threshold: 9, label: "> 9", note: "EPA annual lvl", wss: 52, uxb: 43 },
  { threshold: 12, label: "> 12", note: "", wss: 27, uxb: 20 },
  { threshold: 15, label: "> 15", note: "WHO 24-h", wss: 12, uxb: 11 },
  { threshold: 25, label: "> 25", note: "", wss: 5, uxb: 4 },
  { threshold: 35, label: "> 35", note: "EPA 24-h", wss: 0, uxb: 0 },
];

/** WHO 24-h exceedance site-days by calendar month (both monitors combined). */
export const WHO_EXCEED_BY_MONTH = [0, 0, 0, 0, 0, 11, 7, 5, 0, 0, 0, 0];
export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export const TOP_DAYS = [
  { date: "Aug 5, 2025", site: "Uxbridge", pm25: 33.5, aqi: 96 },
  { date: "Aug 5, 2025", site: "Worcester Summer Street", pm25: 32.9, aqi: 95 },
  { date: "Jul 26, 2025", site: "Worcester Summer Street", pm25: 30.7, aqi: 91 },
  { date: "Jun 8, 2025", site: "Worcester Summer Street", pm25: 29.4, aqi: 89 },
  { date: "Aug 4, 2025", site: "Worcester Summer Street", pm25: 27.4, aqi: 85 },
];
