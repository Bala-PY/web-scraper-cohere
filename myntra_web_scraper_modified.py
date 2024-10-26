from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import requests
import time
import threading
import schedule

# Initialize Flask app
app = Flask(__name__)

# Store scraped data in memory (list of dictionaries) 
scraped_data = []

# Set your Cohere API key
COHERE_API_KEY = 'Enter your Cohere API key here'

# Scrape data function
def scrape_myntra_electronics():
    global scraped_data
    # Set up Selenium WebDriver
    path = 'C:/Users/Bala Eesan/Downloads/chromedriver/chromedriver.exe'
    service = Service(executable_path=path)
    driver = webdriver.Chrome(service=service)

    # Open the Myntra electronics section
    URL = 'https://www.myntra.com/electronics'
    driver.get(URL)
    time.sleep(3)

    # Parse the page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Extract product details
    products = soup.find_all('li', class_='product-base')
    scraped_data = []  # Clear previous data

    for product in products:
        name_tag = product.find('h4', class_='product-product')
        product_name = name_tag.text if name_tag else 'N/A'

        price_tag = product.find('span', class_='product-discountedPrice')
        product_price = price_tag.text if price_tag else 'N/A'

        img_tag = product.find('img', class_='img-responsive')
        product_image = img_tag['src'] if img_tag else 'N/A'

        desc_tag = product.find('h4', class_='product-product')
        product_description = desc_tag.text if desc_tag else 'N/A'

        rating_tag = product.find('div', class_='product-ratingsContainer')
        product_rating = rating_tag.text if rating_tag else 'N/A'

        # Store the extracted data
        scraped_data.append({
            'Product Name': product_name,
            'Price': product_price,
            'Image URL': product_image,
            'Description': product_description,
            'Rating': product_rating,
        })

    driver.quit()
    print("Scraping completed.")
    return scraped_data

# Schedule scraper to run every Monday
def schedule_scraper():
    schedule.every().monday.at("01:00").do(scrape_myntra_electronics)
    
    print("Scheduler is active. Scraping will run every Monday at 01:00 AM.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# Start the scheduler in a separate thread
def run_scheduler():
    scheduler_thread = threading.Thread(target=schedule_scraper)
    scheduler_thread.daemon = True
    scheduler_thread.start()

# Cohere integration to process scraped data and user queries
def query_cohere(query, scraped_data):
    prompt = f"Given the following product details:\n{scraped_data}\n\nAnswer the query: {query}"
    
    headers = {
        'Authorization': f'Bearer {COHERE_API_KEY}',
        'Content-Type': 'application/json',
    }
    
    data = {
        "model": "command",  # Adjust model name if necessary
        "prompt": prompt,
        "max_tokens": 100,  # Adjust token limit based on expected response length
        "temperature": 0.7,
    }
    
    response = requests.post(
        'https://api.cohere.ai/v1/generate',
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        return response.json().get('generations', [{}])[0].get('text', 'No response received from model.')
    else:
        return f"Error: {response.status_code} - {response.json().get('message', 'Unknown error')}"

# API route for querying data
@app.route('/query', methods=['POST'])
def query_scraped_data():
    user_query = request.json.get('query')
    data = scrape_myntra_electronics()
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400
    
    # Format the scraped data into a readable string for querying
    formatted_data = '\n'.join([f"Product: {item['Product Name']}, Price: {item['Price']}, Rating: {item['Rating']}" for item in data])
    
    try:
        # Pass the scraped data and query to Cohere
        cohere_response = query_cohere(user_query, formatted_data)
        return jsonify({'response': cohere_response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Start the Flask app and scheduler
if __name__ == '__main__':
    run_scheduler()  # Start scheduler in background
    app.run(debug=True)
