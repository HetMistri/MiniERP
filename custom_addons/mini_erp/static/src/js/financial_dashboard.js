/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FinancialDashboard extends Component {
    static template = "mini_erp.FinancialDashboard";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.rpc = useService("rpc");
        this.chart1Ref = useRef("chart_income_vs_expenses");
        this.chart2Ref = useRef("chart_revenue_breakdown");
        this.chart3Ref = useRef("chart_profit_trend");
        this.chart4Ref = useRef("chart_expense_categories");

        this.state = useState({
            loading: true,
            filter: 'this_month',
            dateStart: '',
            dateEnd: '',
            kpis: {
                revenue: 0,
                revenue_growth: 0,
                expenses: 0,
                expenses_growth: 0,
                profit: 0,
                remaining_balance: 0,
                cash_utilization: 0,
            },
            health: {
                score: 0,
                status: 'Average'
            },
            summary: {
                today_income: 0,
                today_expenses: 0,
                month_profit: 0,
                ytd_revenue: 0,
                ytd_expenses: 0,
                ytd_profit: 0,
            }
        });

        this.charts = {};

        onMounted(() => {
            this.loadData();
        });

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const params = {
                filter_type: this.state.filter,
            };
            if (this.state.filter === 'custom') {
                params.date_start = this.state.dateStart;
                params.date_end = this.state.dateEnd;
            }

            const data = await this.rpc("/dashboard/financial_data", params);

            this.state.kpis = data.kpis;
            this.state.health = data.health;
            this.state.summary = data.summary;
            this.state.loading = false;

            // Wait for DOM to update then render charts
            setTimeout(() => {
                this.renderCharts(data.charts);
            }, 50);
        } catch (error) {
            console.error("Failed to load financial data", error);
            this.state.loading = false;
        }
    }

    setFilter(filterType) {
        if (this.state.filter === filterType && filterType !== 'custom') return;
        this.state.filter = filterType;
        if (filterType !== 'custom') {
            this.loadData();
        }
    }

    applyCustomRange() {
        if (!this.state.dateStart || !this.state.dateEnd) return;
        this.loadData();
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
    }

    formatPercentage(value) {
        const sign = value >= 0 ? '+' : '';
        return `${sign}${value}%`;
    }

    destroyCharts() {
        Object.keys(this.charts).forEach(key => {
            if (this.charts[key]) {
                this.charts[key].destroy();
            }
        });
        this.charts = {};
    }

    renderCharts(chartData) {
        this.destroyCharts();

        if (typeof Chart === 'undefined') {
            console.error("Chart.js is not loaded in this window.");
            return;
        }

        // 1. Chart 1: Monthly Income vs Expenses (Line Chart)
        if (this.chart1Ref.el) {
            const ctx1 = this.chart1Ref.el.getContext('2d');
            this.charts.chart_income_vs_expenses = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: chartData.monthly_months,
                    datasets: [
                        {
                            label: 'Income',
                            data: chartData.monthly_income,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.05)',
                            borderWidth: 3,
                            tension: 0.4,
                            fill: true
                        },
                        {
                            label: 'Expenses',
                            data: chartData.monthly_expenses,
                            borderColor: '#ef4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.05)',
                            borderWidth: 3,
                            tension: 0.4,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' },
                        tooltip: { mode: 'index', intersect: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.04)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        // 2. Chart 2: Revenue Breakdown (Donut Chart)
        if (this.chart2Ref.el) {
            const ctx2 = this.chart2Ref.el.getContext('2d');
            const totalRevenue = chartData.revenue_breakdown.values.reduce((a, b) => a + b, 0);
            this.charts.chart_revenue_breakdown = new Chart(ctx2, {
                type: 'doughnut',
                data: {
                    labels: chartData.revenue_breakdown.labels,
                    datasets: [{
                        data: chartData.revenue_breakdown.values,
                        backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#3b82f6'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { boxWidth: 12 } },
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    const value = context.raw;
                                    const pct = totalRevenue > 0 ? ((value / totalRevenue) * 100).toFixed(1) : 0;
                                    return ` ${context.label}: ${this.formatCurrency(value)} (${pct}%)`;
                                }
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
        }

        // 3. Chart 3: Profit Trend (Bar Chart)
        if (this.chart3Ref.el) {
            const ctx3 = this.chart3Ref.el.getContext('2d');
            const bgColors = chartData.monthly_profits.map(v => v >= 0 ? 'rgba(16, 185, 129, 0.85)' : 'rgba(239, 68, 68, 0.85)');
            const borderColors = chartData.monthly_profits.map(v => v >= 0 ? '#10b981' : '#ef4444');

            this.charts.chart_profit_trend = new Chart(ctx3, {
                type: 'bar',
                data: {
                    labels: chartData.monthly_months,
                    datasets: [{
                        label: 'Net Profit',
                        data: chartData.monthly_profits,
                        backgroundColor: bgColors,
                        borderColor: borderColors,
                        borderWidth: 1.5,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            grid: { color: 'rgba(0, 0, 0, 0.04)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }

        // 4. Chart 4: Expense Categories (Horizontal Bar Chart)
        if (this.chart4Ref.el) {
            const ctx4 = this.chart4Ref.el.getContext('2d');
            this.charts.chart_expense_categories = new Chart(ctx4, {
                type: 'bar',
                data: {
                    labels: chartData.expense_categories.labels,
                    datasets: [{
                        label: 'Amount Spent',
                        data: chartData.expense_categories.values,
                        backgroundColor: '#f59e0b',
                        borderRadius: 4,
                        barThickness: 16
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.04)' }
                        },
                        y: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    }
}

registry.category("fields").add("financial_dashboard", {
    component: FinancialDashboard,
});
