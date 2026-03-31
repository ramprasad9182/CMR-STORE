# Advanced Real-time POS Dashboard

A comprehensive Odoo addon for Point of Sale systems that provides real-time dashboards and order management capabilities.

## Features

- **Real-time Dashboard**: Monitor sales metrics in real-time
- **Order Management**: Create, view, and manage POS orders
- **Database Sync**: Sync orders to external databases
- **Sales Analytics**: Track total sales, order count, average order value, and items sold
- **Multi-POS Support**: Configure dashboards for multiple POS stations

## Installation

1. Copy the addon to your Odoo addons directory
2. Update the addons list in Odoo
3. Install the "Advanced Real-time POS Dashboard" addon

## Configuration

1. Navigate to Point of Sale → POS Dashboard
2. Create a new dashboard
3. Select the POS configurations to monitor
4. Set the date range for metrics
5. View real-time sales statistics

## Usage

### Creating a Dashboard

1. Go to POS Dashboard menu
2. Click Create
3. Enter dashboard name
4. Select POS configurations
5. Save and view metrics

### Syncing Orders

Orders are automatically synced to the dashboard when they are paid. You can also manually sync orders using the "Sync to Database" button on order forms.

## Models

- **pos.dashboard**: Main dashboard model for displaying metrics
- **pos.dashboard.line**: Dashboard line items for customized metrics
- **pos.order**: Extended with database sync functionality

## Technical Stack

- Python (Odoo backend)
- XML (Views)
- JavaScript (Real-time updates)
- CSS (Styling)

## Support

For support and issues, contact the development team.
