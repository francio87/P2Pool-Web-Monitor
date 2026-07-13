export function createChartRenderer() {
  let hashrateChartInstance = null;
  let sharesChartInstance = null;

  function buildChartOptions(text, grid, tickLimit) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          labels: {
            color: text,
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true,
            pointStyle: 'circle',
          },
        },
      },
      scales: {
        x: { grid: { color: grid }, ticks: { color: text, maxTicksLimit: tickLimit } },
        y: { grid: { color: grid }, ticks: { color: text }, beginAtZero: true },
      },
    };
  }

  function renderCharts(payload) {
    if (typeof Chart === 'undefined') {
      return;
    }

    const style = getComputedStyle(document.documentElement);
    const text = style.getPropertyValue('--text-muted').trim();
    const grid = style.getPropertyValue('--chart-grid').trim();
    const chart15m = style.getPropertyValue('--chart-15m').trim();
    const chart15mFill = style.getPropertyValue('--chart-15m-fill').trim();
    const chart1h = style.getPropertyValue('--chart-1h').trim();
    const danger = style.getPropertyValue('--danger').trim();

    const labels = payload.history?.labels || [];
    const hr15m = payload.history?.hr15m || [];
    const hr1h = payload.history?.hr1h || [];
    const shares = payload.history?.shares || [];
    const manyPoints = labels.length > 72;
    const pointRadius = manyPoints ? 0 : 1.3;
    const tickLimit = manyPoints ? 10 : 14;
    const commonOptions = buildChartOptions(text, grid, tickLimit);

    if (!hashrateChartInstance) {
      hashrateChartInstance = new Chart(document.getElementById('hashrateChart'), {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: '15m Estimate',
              data: hr15m,
              borderColor: chart15m,
              backgroundColor: chart15mFill,
              fill: true,
              tension: 0.3,
              pointRadius,
              borderWidth: 2.6,
            },
            {
              label: '1h Estimate',
              data: hr1h,
              borderColor: chart1h,
              tension: 0.3,
              pointRadius,
              borderWidth: 2.2,
              borderDash: [6, 4],
            },
          ],
        },
        options: commonOptions,
      });
    } else {
      hashrateChartInstance.data.labels = labels;
      hashrateChartInstance.data.datasets[0].data = hr15m;
      hashrateChartInstance.data.datasets[0].borderColor = chart15m;
      hashrateChartInstance.data.datasets[0].backgroundColor = chart15mFill;
      hashrateChartInstance.data.datasets[0].pointRadius = pointRadius;
      hashrateChartInstance.data.datasets[1].data = hr1h;
      hashrateChartInstance.data.datasets[1].borderColor = chart1h;
      hashrateChartInstance.data.datasets[1].pointRadius = pointRadius;
      hashrateChartInstance.options = commonOptions;
      hashrateChartInstance.update('none');
    }

    if (!sharesChartInstance) {
      sharesChartInstance = new Chart(document.getElementById('sharesChart'), {
        type: 'line',
        data: {
          labels,
          datasets: [{ label: 'Shares Delta', data: shares, borderColor: danger, stepped: true, pointRadius: manyPoints ? 0 : 1.5, borderWidth: 2 }],
        },
        options: commonOptions,
      });
    } else {
      sharesChartInstance.data.labels = labels;
      sharesChartInstance.data.datasets[0].data = shares;
      sharesChartInstance.data.datasets[0].borderColor = danger;
      sharesChartInstance.data.datasets[0].pointRadius = manyPoints ? 0 : 1.5;
      sharesChartInstance.options = commonOptions;
      sharesChartInstance.update('none');
    }
  }

  return renderCharts;
}
