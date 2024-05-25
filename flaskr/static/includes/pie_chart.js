function drawPieChart(assetData) {
    var data = [{
        values: assetData.map(asset => asset.value),
        labels: assetData.map(asset => asset.label),
        type: 'pie'
    }];
  
    var layout = {
        title: 'Asset Distribution',
        height: 400,
        width: 500
    };
  
    Plotly.newPlot('assetChart', data, layout);
  }