// Dashboard Charts JavaScript
// This file contains the chart initialization and update logic

// Function to generate dynamic colors
function generateColors(num) {
    const colors = [];
    for (let i = 0; i < num; i++) {
        const hue = (i * 137.508) % 360;
        colors.push(`hsl(${hue}, 70%, 60%)`);
    }
    return colors;
}

// Variables to hold chart instances
let departmentAssetChartInstance = null;
let assetFlowChartInstance = null;

// Initialize dashboard charts
function initializeDashboardCharts(data) {
    const {
        assetTypeLabels,
        assetTypeCounts,
        departmentLabels,
        departmentAssetCounts,
        dayLabels,
        assignedPerDay,
        returnedPerDay,
        assetStatusLabels,
        assetStatusCounts,
        noDepartmentDataMsg,
        assetAssignedLabel
    } = data;

    // Asset Type Chart (Pie Chart)
    if (assetTypeLabels && assetTypeLabels.length > 0 && !(assetTypeLabels.length === 1 && assetTypeLabels[0] === 'No Data')) {
        const assetTypeCtx = document.getElementById('assetTypeChart').getContext('2d');
        new Chart(assetTypeCtx, {
            type: 'pie',
            data: {
                labels: assetTypeLabels,
                datasets: [{
                    data: assetTypeCounts,
                    backgroundColor: generateColors(assetTypeLabels.length),
                    borderColor: '#ffffff',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    title: {
                        display: false
                    }
                }
            }
        });
    } else {
         document.getElementById('assetTypeChart').parentElement.innerHTML = '<p class="text-muted text-center mt-4">データがありません</p>';
    }

    // Department Asset Chart (Bar Chart)
     if (departmentLabels && departmentLabels.length > 0 && !(departmentLabels.length === 1 && departmentLabels[0] === 'No Data')) {
        const departmentAssetCtx = document.getElementById('departmentAssetChart').getContext('2d');
        departmentAssetChartInstance = new Chart(departmentAssetCtx, {
            type: 'bar',
            data: {
                labels: departmentLabels,
                datasets: [{
                    label: assetAssignedLabel || 'Number of Assigned Assets',
                    data: departmentAssetCounts,
                     backgroundColor: generateColors(departmentLabels.length),
                     borderColor: generateColors(departmentLabels.length).map(color => color.replace('60%', '40%')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                     title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
     } else {
          document.getElementById('departmentAssetChart').parentElement.innerHTML = `<p class="text-muted text-center mt-4">${noDepartmentDataMsg}</p>`;
     }

     // Asset Flow Chart (Line Chart)
     if (dayLabels && dayLabels.length > 0) {
         const assetFlowCtx = document.getElementById('assetFlowChart').getContext('2d');
         assetFlowChartInstance = new Chart(assetFlowCtx, {
             type: 'line',
             data: {
                 labels: dayLabels,
                 datasets: [
                     {
                         label: '割り当て済み',
                         data: assignedPerDay,
                         borderColor: 'rgb(75, 192, 192)',
                         backgroundColor: 'rgba(75, 192, 192, 0.1)',
                         tension: 0.1,
                         fill: true
                     },
                      {
                         label: '返却済み',
                         data: returnedPerDay,
                         borderColor: 'rgb(255, 99, 132)',
                         backgroundColor: 'rgba(255, 99, 132, 0.1)',
                         tension: 0.1,
                         fill: true
                     }
                 ]
             },
             options: {
                 responsive: true,
                 maintainAspectRatio: false,
                  plugins: {
                     title: {
                        display: false
                    }
                 },
                 scales: {
                    y: {
                        beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                    }
                }
             }
         });
     } else {
          document.getElementById('assetFlowChart').parentElement.innerHTML = '<p class="text-muted text-center mt-4">No recent assignment/return data.</p>';
     }

     // Event listeners for time filters
     document.querySelectorAll('.dropdown-menu .dropdown-item').forEach(item => {
         item.addEventListener('click', function(e) {
             e.preventDefault();
             const filter = this.getAttribute('data-filter');
             const button = this.closest('.dropdown').querySelector('.dropdown-toggle');
             const cardHeader = this.closest('.card-header');

             if (cardHeader.parentElement.querySelector('#departmentAssetChart')) {
                 button.textContent = this.textContent;
                 updateDepartmentAssetChart(filter);
             } else if (cardHeader.parentElement.querySelector('#assetFlowChart')) {
                  button.textContent = this.textContent;
                  updateAssetFlowChart(filter);
             }
         });
     });
}

// Function to update Department Asset Chart data
function updateDepartmentAssetChart(filter) {
    fetch(`/api/department_assets?filter=${filter}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (departmentAssetChartInstance) {
                departmentAssetChartInstance.data.labels = data.labels;
                departmentAssetChartInstance.data.datasets[0].data = data.counts;
                departmentAssetChartInstance.update();
            }
        })
        .catch(error => console.error('Error fetching department asset data:', error));
}

// Function to update Asset Flow Chart data
function updateAssetFlowChart(filter) {
     fetch(`/api/asset_flow?filter=${filter}`)
         .then(response => {
             if (!response.ok) {
                 throw new Error(`HTTP error! status: ${response.status}`);
             }
             return response.json();
         })
         .then(data => {
             if (assetFlowChartInstance) {
                assetFlowChartInstance.data.labels = data.labels;
                assetFlowChartInstance.data.datasets[0].data = data.assigned;
                assetFlowChartInstance.data.datasets[1].data = data.returned;
                assetFlowChartInstance.update();
             }
         })
         .catch(error => console.error('Error fetching asset flow data:', error));
} 