import mysql.connector
import re
from flask import Flask, render_template, request
import openai

app = Flask(__name__, static_folder='static')

# Replace with your actual OpenAI API key
openai.api_key = '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'

# Database configuration
db_config = {
    'user': 'root',
    'password': 'Jhoncena7@',
    'host': 'localhost',
    'database': 'productdb'
}

def extract_model_name(user_input):
    ignore_keywords = [
        "tell me about", "what can you tell me about", 
        "give me details on", "information about", "details of",
        "the", "is", "are", "of", "minimum price of", "maximum price of",
        "price of", "list of"
    ]
    
    # Remove punctuation and convert to lowercase for easier matching
    user_input = re.sub(r'[^\w\s]', '', user_input.lower())
    
    for keyword in ignore_keywords:
        user_input = user_input.replace(keyword, "")
    
    # Remove any extra spaces
    model_name = ' '.join(user_input.split())
    
    return model_name.strip()


def get_product_price(user_input):
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Database connected successfully.")

        cursor = connection.cursor()

        # Log user input
        print(f"User input: {user_input}")

        # Initialize variables for query
        category = None
        model_name = None
        query_type = None

        # Define keywords for specific product inquiries
        specific_product_keywords = [
            "tell me about", "what can you tell me about",
            "give me details on", "information about", "details of"
        ]

        # Check for specific product name in the query
        if any(keyword in user_input for keyword in specific_product_keywords):
            model_name = extract_model_name(user_input)
            print(f"Extracted model name: {model_name}")
            query = "SELECT model, price FROM products WHERE LOWER(model) LIKE %s;"
            cursor.execute(query, ('%' + model_name + '%',))
            result = cursor.fetchone()

            if result:
                print(f"Query result: {result}")
                return result[0], result[1]
            else:
                print("No results found for the specific product.")
                return None, None

        # Check if asking for the cheapest or most expensive
        if "most expensive" in user_input.lower() or "highest price" in user_input.lower():
            query_type = "max"
        elif "cheapest" in user_input.lower() or "lowest price" in user_input.lower():
            query_type = "min"

        # Check the category of the product (phone, laptop, tablet)
        if "laptop" in user_input.lower():
            category = "laptop"
        elif "phone" in user_input.lower():
            category = "phone"
        elif "tablet" in user_input.lower():
            category = "tablet"

        # If it's asking for the most expensive or cheapest product
        if query_type and category:
            if query_type == "max":
                query = "SELECT model, price FROM products WHERE category = %s ORDER BY price DESC LIMIT 1;"
            elif query_type == "min":
                query = "SELECT model, price FROM products WHERE category = %s ORDER BY price ASC LIMIT 1;"
            
            print(f"Executing query: {query} with category: {category}")
            cursor.execute(query, (category,))
            result = cursor.fetchone()
            
            if result:
                print(f"Query result: {result}")
                return result[0], result[1]
            else:
                print(f"No results found for the category: {category}")
                return None, None
        
        # If asking for the list of products in a category
        if "list of" in user_input.lower() and category:
            query = "SELECT model, price FROM products WHERE category = %s;"
            print(f"Executing query for list: {query} with category: {category}")
            cursor.execute(query, (category,))
            result = cursor.fetchall()

            if result:
                print(f"Query result: {result}")
                return result, None  # Return the list of products
            else:
                print(f"No results found for the category: {category}")
                return None, None

        # Handle general queries that might not fit into specific categories
        model_name = extract_model_name(user_input)
        if model_name:
            print(f"General inquiry about: {model_name}")
            query = "SELECT model, price FROM products WHERE LOWER(model) LIKE %s;"
            cursor.execute(query, ('%' + model_name + '%',))
            result = cursor.fetchone()
            if result:
                return result[0], result[1]
            else:
                return None, None

        cursor.close()
        connection.close()

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return None, None



@app.route("/", methods=["GET", "POST"])
def chat():
    products = None  # Initialize products variable
    answer = ""
    
    if request.method == "POST":
        user_input = request.form['user_input']

        # Fetch the relevant product and price from the database based on user input
        result, price = get_product_price(user_input)

        # Handle cases where no product was found
        if result is None:
            answer = "I'm sorry, but I couldn't find the information you requested."
        elif isinstance(result, list):  # If the result is a list of products (for "list of" queries)
            products = result  # Store the list of products for rendering in the template
            answer = "Here is the list of available products:"

        else:
            # Construct the prompt for OpenAI Chat API for single product
            prompt = f"User asked: {user_input}\nThe product is '{result}' priced at ${price}. Please provide a concise response."

            try:
                # Call OpenAI's ChatCompletion API using GPT-4 model
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50  # Limit tokens to keep response short
                )

                # Extract the response content
                answer = response['choices'][0]['message']['content'].strip()

                # If the response is too long or not concise, return a fallback response
                if not answer or len(answer.split()) > 20:  # Check if response is concise
                    answer = f"The product is '{result}' priced at ${price:,.2f}."

            except openai.OpenAIError as e:
                answer = f"OpenAI API error: {e}"
            except Exception as e:
                answer = f"Other error: {e}"

        # Render the template with the user input and answer
        return render_template("chat.html", user_input=user_input, answer=answer, products=products)

    return render_template("chat.html")

if __name__ == "__main__":
    app.run(debug=True)
