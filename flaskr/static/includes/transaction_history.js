function showLatestTransactions() {
    const transactionRecords = document.querySelectorAll('.transaction-record');
    transactionRecords.forEach(record => record.style.display = 'none');
    for (let i = 0; i < Math.min(5, transactionRecords.length); i++) {
        transactionRecords[i].style.display = '';
    }
    document.getElementById('showMoreBtn').style.display = '';
    document.getElementById('showLessBtn').style.display = 'none';
}

function showAllTransactions() {
    document.querySelectorAll('.transaction-record').forEach(record => record.style.display = '');
    document.getElementById('showMoreBtn').style.display = 'none';
    document.getElementById('showLessBtn').style.display = '';
}

document.getElementById('showMoreBtn').addEventListener('click', showAllTransactions);
document.getElementById('showLessBtn').addEventListener('click', showLatestTransactions);

window.onload = () => {
    let symbolField = document.getElementById('submittedSymbol');
    if (symbolField && symbolField.value) makePlot(symbolField.value);
    showLatestTransactions();
};
