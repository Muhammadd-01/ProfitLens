import csv
import random
import datetime
import os

# Set random seed for reproducibility
random.seed(42)

# Constants
NUM_PRODUCTS = 100
NUM_CUSTOMERS = 10_000
NUM_ORDERS = 50_000
NUM_REVIEWS = 5_000

# File names
PRODUCTS_FILE = 'products.csv'
CUSTOMERS_FILE = 'customers.csv'
ORDERS_FILE = 'orders.csv'
REVIEWS_FILE = 'reviews.csv'
DENORMALIZED_FILE = 'business_data.csv'

# Categories and their price ranges
CATEGORIES = {
    'Electronics': (50.0, 2000.0),
    'Clothing': (15.0, 200.0),
    'Home & Garden': (20.0, 500.0),
    'Sports': (10.0, 300.0),
    'Books': (5.0, 50.0),
    'Beauty': (10.0, 150.0),
    'Food & Beverage': (5.0, 100.0),
    'Office Supplies': (5.0, 200.0)
}

# 1. Generate Products
def generate_products():
    """Generates 100 realistic products across 8 categories with assigned weights for popularity."""
    products = []
    adjectives = ["Premium", "Standard", "Basic", "Advanced", "Ultra", "Smart", "Classic", "Modern", "Eco-friendly", "Durable"]
    nouns = {
        'Electronics': ["Smartphone", "Laptop", "Headphones", "Tablet", "Monitor", "Keyboard", "Mouse", "Speaker"],
        'Clothing': ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Sweater", "Dress", "Shorts", "Socks"],
        'Home & Garden': ["Planter", "Chair", "Lamp", "Rug", "Vase", "Table", "Cushion", "Blender"],
        'Sports': ["Basketball", "Yoga Mat", "Dumbbells", "Tennis Racket", "Running Shoes", "Water Bottle", "Towel", "Gym Bag"],
        'Books': ["Novel", "Biography", "Cookbook", "Sci-Fi", "History Book", "Dictionary", "Guide", "Journal"],
        'Beauty': ["Moisturizer", "Lipstick", "Perfume", "Shampoo", "Conditioner", "Serum", "Sunscreen", "Mascara"],
        'Food & Beverage': ["Coffee Beans", "Tea", "Chocolate", "Olive Oil", "Honey", "Nuts", "Protein Bar", "Juice"],
        'Office Supplies': ["Notebook", "Pen Set", "Desk Organizer", "Stapler", "Paper", "Folder", "Whiteboard", "Calculator"]
    }
    
    for i in range(1, NUM_PRODUCTS + 1):
        category = random.choice(list(CATEGORIES.keys()))
        min_price, max_price = CATEGORIES[category]
        name = f"{random.choice(adjectives)} {random.choice(nouns[category])}"
        
        # Power law distribution for popularity
        weight = random.betavariate(1, 5)
        
        product = {
            'product_id': f"P{i:04d}",
            'name': name,
            'category': category,
            'unit_price': round(random.uniform(min_price, max_price), 2),
            'description': f"A high-quality {name.lower()} in the {category} category.",
            'weight': weight # Internal use for popularity
        }
        products.append(product)
        
    # Ensure top 20% products generate ~60% of revenue/orders
    products.sort(key=lambda x: x['weight'], reverse=True)
    for i in range(int(NUM_PRODUCTS * 0.2)):
        products[i]['weight'] *= 10
        
    return products

# 2. Generate Customers
def generate_customers():
    """Generates 10k customers with injected missing values (emails, regions) and heavy buyer flags."""
    customers = []
    first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    regions = ["North", "South", "East", "West", "Central"]
    
    start_date = datetime.date(2021, 1, 1)
    end_date = datetime.date(2023, 12, 31)
    days_between_dates = (end_date - start_date).days
    
    for i in range(1, NUM_CUSTOMERS + 1):
        first = random.choice(first_names)
        last = random.choice(last_names)
        name = f"{first} {last}"
        
        email = f"{first.lower()}.{last.lower()}{random.randint(1,9999)}@example.com"
        if random.random() < 0.04: # ~4% missing emails
            email = ""
            
        region = random.choice(regions)
        if random.random() < 0.02: # ~2% missing regions
            region = ""
            
        random_number_of_days = random.randrange(days_between_dates)
        join_date = start_date + datetime.timedelta(days=random_number_of_days)
        
        # Heavy buyers flag (top 10%)
        is_heavy_buyer = (i <= NUM_CUSTOMERS * 0.1)
        
        customer = {
            'customer_id': f"C{i:05d}",
            'name': name,
            'email': email,
            'region': region,
            'join_date': join_date.strftime("%Y-%m-%d"),
            'is_heavy_buyer': is_heavy_buyer # Internal use
        }
        customers.append(customer)
        
    return customers

# 3. Generate Orders
def get_seasonal_date(year):
    """Generates dates skewed towards holiday season (Nov-Dec)."""
    month_weights = [0.5, 0.5, 0.8, 0.9, 1.0, 1.0, 1.1, 1.1, 1.0, 1.2, 1.8, 2.0]
    month = random.choices(range(1, 13), weights=month_weights, k=1)[0]
    
    days_in_month = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
    day = random.randint(1, days_in_month[month])
    
    return datetime.date(year, month, day)

def generate_orders(products, customers):
    """Generates 50k orders handling anomalies, duplicates, heavy buyers, and seasonality."""
    orders = []
    
    heavy_buyers = [c for c in customers if c['is_heavy_buyer']]
    regular_buyers = [c for c in customers if not c['is_heavy_buyer']]
    
    product_weights = [p['weight'] for p in products]
    
    statuses = ['completed', 'processing', 'cancelled', 'refunded']
    status_weights = [0.85, 0.08, 0.05, 0.02]
    
    channels = ['online', 'in-store', 'mobile']
    channel_weights = [0.60, 0.25, 0.15]
    
    quantities = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    quantity_weights = [50, 20, 10, 5, 4, 3, 3, 2, 2, 1]
    
    discounts = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    discount_weights = [70, 10, 8, 5, 3, 2, 2]

    num_heavy_orders = int(NUM_ORDERS * 0.4)
    num_regular_orders = NUM_ORDERS - num_heavy_orders
    
    order_customers = random.choices(heavy_buyers, k=num_heavy_orders) + random.choices(regular_buyers, k=num_regular_orders)
    order_products = random.choices(products, weights=product_weights, k=NUM_ORDERS)
    
    for i in range(NUM_ORDERS):
        customer = order_customers[i]
        product = order_products[i]
        
        year = random.choice([2024, 2025])
        order_date = get_seasonal_date(year)
        
        quantity = random.choices(quantities, weights=quantity_weights, k=1)[0]
        discount = random.choices(discounts, weights=discount_weights, k=1)[0]
        status = random.choices(statuses, weights=status_weights, k=1)[0]
        channel = random.choices(channels, weights=channel_weights, k=1)[0]
        
        unit_price = product['unit_price']
        amount = round(unit_price * quantity * (1 - discount), 2)
        
        order = {
            'order_id': f"ORD-{100000 + i}",
            'customer_id': customer['customer_id'],
            'product_id': product['product_id'],
            'order_date': order_date.strftime("%Y-%m-%d"),
            'quantity': quantity,
            'unit_price': unit_price,
            'discount': discount,
            'amount': amount,
            'status': status,
            'region': customer['region'],
            'channel': channel
        }
        orders.append(order)

    # Anomalies
    num_anomalies = random.randint(5, 10)
    for _ in range(num_anomalies):
        idx = random.randint(0, NUM_ORDERS - 1)
        orders[idx]['quantity'] = random.randint(50, 100)
        orders[idx]['amount'] = round(orders[idx]['unit_price'] * orders[idx]['quantity'], 2)
        
    # Duplicates (~0.5%)
    num_duplicates = int(NUM_ORDERS * 0.005)
    for _ in range(num_duplicates):
        idx = random.randint(0, NUM_ORDERS - 1)
        dup_order = orders[idx].copy()
        orders.append(dup_order)
        
    orders.sort(key=lambda x: x['order_date'])
    return orders

# 4. Generate Reviews
def generate_reviews(orders):
    """Generates 5k reviews for completed orders with ratings skewed towards positive."""
    reviews = []
    
    positive = ["Great product!", "Love this.", "Exceeded expectations.", "Five stars!", "Fantastic quality.", "Very satisfied.", "Worth every penny.", "Exactly as described."]
    neutral = ["It's okay.", "Average.", "Not bad.", "Decent quality.", "Met expectations.", "Just average.", "Fairly priced."]
    negative = ["Poor quality.", "Terrible.", "Waste of money.", "Disappointed.", "Arrived damaged.", "Not as described.", "Regret this purchase."]
    
    completed_orders = [o for o in orders if o['status'] == 'completed']
    unique_completed_orders = list({o['order_id']: o for o in completed_orders}.values())
    review_orders = random.sample(unique_completed_orders, min(NUM_REVIEWS, len(unique_completed_orders)))
    
    for i, order in enumerate(review_orders):
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 5, 10, 30, 50], k=1)[0]
        template = random.choice(positive if rating >= 4 else (neutral if rating == 3 else negative))
        
        order_date = datetime.datetime.strptime(order['order_date'], "%Y-%m-%d").date()
        review_date = order_date + datetime.timedelta(days=random.randint(1, 60))
        
        review = {
            'review_id': f"REV-{10000 + i}",
            'customer_id': order['customer_id'],
            'product_id': order['product_id'],
            'order_id': order['order_id'],
            'rating': rating,
            'review_text': template,
            'review_date': review_date.strftime("%Y-%m-%d")
        }
        reviews.append(review)
        
    return reviews

def save_to_csv(filename, data, fieldnames):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)

def main():
    print("Generating synthetic data for ProfitLens...")
    
    products = generate_products()
    customers = generate_customers()
    orders = generate_orders(products, customers)
    reviews = generate_reviews(orders)
    
    products_dict = {p['product_id']: p for p in products}
    customers_dict = {c['customer_id']: c for c in customers}
    
    denormalized = []
    for order in orders:
        c = customers_dict[order['customer_id']]
        p = products_dict[order['product_id']]
        
        row = order.copy()
        row['customer_name'] = c['name']
        row['customer_email'] = c['email']
        row['customer_join_date'] = c['join_date']
        row['product_name'] = p['name']
        row['product_category'] = p['category']
        row['product_description'] = p['description']
        denormalized.append(row)
        
    save_to_csv(PRODUCTS_FILE, products, ['product_id', 'name', 'category', 'unit_price', 'description'])
    save_to_csv(CUSTOMERS_FILE, customers, ['customer_id', 'name', 'email', 'region', 'join_date'])
    save_to_csv(ORDERS_FILE, orders, ['order_id', 'customer_id', 'product_id', 'order_date', 'quantity', 'unit_price', 'discount', 'amount', 'status', 'region', 'channel'])
    save_to_csv(REVIEWS_FILE, reviews, ['review_id', 'customer_id', 'product_id', 'order_id', 'rating', 'review_text', 'review_date'])
    
    denormalized_fields = [
        'order_id', 'order_date', 'customer_id', 'customer_name', 'customer_email', 'region', 'customer_join_date',
        'product_id', 'product_name', 'product_category', 'product_description',
        'quantity', 'unit_price', 'discount', 'amount', 'status', 'channel'
    ]
    save_to_csv(DENORMALIZED_FILE, denormalized, denormalized_fields)
    
    summary = f"""
✓ ProfitLens Synthetic Data Generated
  Products:  {len(products):,}
  Customers: {len(customers):,}
  Orders:    {len(orders):,}
  Reviews:   {len(reviews):,}
  
  Files created:
    {PRODUCTS_FILE}
    {CUSTOMERS_FILE}
    {ORDERS_FILE}
    {REVIEWS_FILE}
    {DENORMALIZED_FILE} (denormalized — ready for upload)
  
  ⚠ This is synthetic data for development/testing only.
"""
    print(summary)

if __name__ == "__main__":
    main()
