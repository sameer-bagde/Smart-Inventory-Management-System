import nbformat
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import streamlit as st
import matplotlib.pyplot as plt

# Function to calculate Safety Stock
def calculate_safety_stock(demand_variance, lead_time, z_score=1.96):
    return z_score * np.sqrt(lead_time * demand_variance)

# Function to calculate Economic Order Quantity (EOQ)
def calculate_eoq(demand, ordering_cost, holding_cost):
    return np.sqrt((2 * demand * ordering_cost) / holding_cost)

# Function to calculate Reorder Point (ROP)
def calculate_reorder_point(daily_demand, lead_time, safety_stock):
    return (daily_demand * lead_time) + safety_stock

# Function for Total Cost optimization
def total_inventory_cost(order_qty, demand, holding_cost, ordering_cost, stockout_cost, lead_time, safety_stock):
    avg_inventory = order_qty / 2 + safety_stock
    holding_cost_total = avg_inventory * holding_cost
    ordering_cost_total = demand / order_qty * ordering_cost
    stockout_occurrences = max(0, demand - order_qty)
    stockout_cost_total = stockout_occurrences * stockout_cost
    return holding_cost_total + ordering_cost_total + stockout_cost_total

# Optimization for EOQ
def optimize_inventory(demand, holding_cost, ordering_cost, stockout_cost, lead_time, safety_stock):
    result = minimize(total_inventory_cost, 
                      x0=100,
                      args=(demand, holding_cost, ordering_cost, stockout_cost, lead_time, safety_stock),
                      bounds=((1, None),))
    return result.x[0]

# Load the notebook and extract the df_inventory DataFrame
def load_df_inventory_from_notebook(notebook_path):
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook_content = nbformat.read(f, as_version=4)
    
    # Find the cell that contains the DataFrame 'df_inventory'
    for cell in notebook_content.cells:
        if cell.cell_type == 'code' and 'df_inventory' in cell.source:
            # Execute the code in the notebook cell to create df_inventory
            exec(cell.source)
    
    return df_inventory

# Load df_inventory from the notebook
df_inventory = load_df_inventory_from_notebook('inventory-forecast.ipynb')

# Calculate sales efficiency for all products
df_inventory['sales_efficiency'] = df_inventory['avg_items_sold_per_month'] / df_inventory['inventory_qty']
average_efficiency = df_inventory['sales_efficiency'].mean()

# Define a threshold for overstock detection (adjustable based on your data)
efficiency_threshold = average_efficiency * 0.5

# Results for plotting and display
optimization_results = []

# Process each product in df_inventory
for index, row in df_inventory.iterrows():
    demand_per_year = row['total_items_sold'] * 12
    daily_demand = demand_per_year / 365
    lead_time_days = row['lead_time_days']
    holding_cost_per_unit = row['original_price_per_unit'] * 0.05
    ordering_cost_per_order = 50
    stockout_cost_per_unit = 10
    current_inventory = row['inventory_qty']
    demand_variance = row['avg_items_sold_per_month'] * 0.5

    # Calculate Safety Stock
    safety_stock = calculate_safety_stock(demand_variance, lead_time_days)
    
    # Calculate EOQ
    eoq = calculate_eoq(demand_per_year, ordering_cost_per_order, holding_cost_per_unit)
    
    # Calculate Reorder Point
    reorder_point = calculate_reorder_point(daily_demand, lead_time_days, safety_stock)
    
    # Optimize Inventory using cost minimization
    optimal_order_qty = optimize_inventory(demand_per_year, holding_cost_per_unit, ordering_cost_per_order,
                                           stockout_cost_per_unit, lead_time_days, safety_stock)
    
    # Calculate product's sales efficiency
    sales_efficiency = row['avg_items_sold_per_month'] / current_inventory
    
    # Determine inventory status
    if current_inventory > eoq:
        if sales_efficiency < efficiency_threshold:
            inventory_status = 'Overstock'
        else:
            inventory_status = 'Excess Stock (but selling well)'
    elif current_inventory < reorder_point:
        inventory_status = 'Understock'
    else:
        inventory_status = 'Optimal'

    # Append results for visualization
    optimization_results.append({
        'Product Name': row['product_name'],
        'EOQ': eoq,
        'Reorder Point': reorder_point,
        'Safety Stock': safety_stock,
        'Optimized Order Quantity': optimal_order_qty,
        'Sales Efficiency': sales_efficiency,
        'Inventory Status': inventory_status
    })

# Convert the results into a DataFrame
df_results = pd.DataFrame(optimization_results)

# Display in Streamlit
st.title("Inventory Optimization Dashboard")
st.write("### Optimized Inventory Details")
st.dataframe(df_results)

# Plot EOQ and Reorder Points for each product
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(df_results['Product Name'], df_results['EOQ'], label='EOQ', alpha=0.6, color='blue')
ax.bar(df_results['Product Name'], df_results['Reorder Point'], label='Reorder Point (ROP)', alpha=0.6, color='red')
ax.set_ylabel("Quantity")
ax.set_title("EOQ vs Reorder Point")
ax.legend()

st.pyplot(fig)

# Plot Safety Stock and Optimized Order Quantity
fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.bar(df_results['Product Name'], df_results['Safety Stock'], label='Safety Stock', alpha=0.6, color='green')
ax2.bar(df_results['Product Name'], df_results['Optimized Order Quantity'], label='Optimized Order Qty', alpha=0.6, color='orange')
ax2.set_ylabel("Quantity")
ax2.set_title("Safety Stock vs Optimized Order Quantity")
ax2.legend()

st.pyplot(fig2)

# Display Inventory Status as a pie chart
inventory_status_counts = df_results['Inventory Status'].value_counts()
fig3, ax3 = plt.subplots(figsize=(8, 8))
ax3.pie(inventory_status_counts, labels=inventory_status_counts.index, autopct='%1.1f%%', startangle=90, colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
ax3.set_title('Inventory Status Distribution')

st.pyplot(fig3)
