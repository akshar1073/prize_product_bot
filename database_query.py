import mysql.connector
import openai

# Connect to MySQL database
def get_max_price_product():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Jhoncena7@",
        database="productdb"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT product, price FROM products ORDER BY price DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result

# Example function using OpenAI API (API key needs xto be set)
def query_openai_for_product():
    product, price = get_max_price_product()
    openai.api_key = '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'
    prompt = f"The product with the highest price is {product} which costs {price}. Please confirm."
    
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=50
    )
    
    return response.choices[0].text.strip()

# Test the function
print(query_openai_for_product())
