function retrieveAction(event){
  event.preventDefault();
  let symbol = document.getElementById('symbol').value;
  if(symbol) {
      symbol = symbol.trim().toUpperCase();
      window.location.pathname = `/stock/${symbol}`;
  }
}

function makePlot(stockSymbol) {
  fetch('/stock/pricing/'+stockSymbol)
  .then(response => response.json())
  .then(data => {
    // Create Plotly chart
    const chartData = [{
      x: data.dates,
      y: data.adjClosePrices,
      type: 'scatter',
      mode: 'lines',
      marker: {
        color: 'blue'
      }
    }];

    const layout = {
      title: 'Stock Daily Prices for ' + data.symbol,
      xaxis: {
        title: 'Date'
      },
      yaxis: {
        title: 'Price'
      }
    };

    Plotly.newPlot('myChart', chartData, layout);
  })
  .catch(error => {
    console.error('Error fetching data:', error);
  });

}

document.getElementById('searchForm').addEventListener('submit', retrieveAction);

window.onload = (event) => {
  let symbolField = document.getElementById('submittedSymbol');
  if (symbolField && symbolField.value) {
    makePlot(symbolField.value)
  }    
};