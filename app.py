import mysql.connector
import re
from flask import Flask, render_template, request, session
import openai
from dotenv import load_dotenv
import os


dotenv_path = "D:\\LLMproject\\.env"  # Using double backslashes

load_dotenv(dotenv_path=dotenv_path)
print("Loaded .env file:", dotenv_path)
api_key = os.getenv("OPENAI_API_KEY")
print("API Key:", api_key)  # This will print the API key to the console for debugging

if api_key is None:
    raise ValueError("OpenAI API key not found. Please set it in your .env file.")
app = Flask(__name__, static_folder='static')
app.secret_key = 'ab07ef46de54c42b1ad9652b0035004c'  # Us

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
        elif "cheapest" in user_input.lower() or "lowest price" in user_input.lower() or "minimum price" in user_input.lower():
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

        # Handle general queries for minimum and maximum price for any category
        if "minimum price" in user_input.lower() or "maximum price" in user_input.lower():
            if "laptop" in user_input.lower():
                category = "laptop"
            elif "tablet" in user_input.lower():
                category = "tablet"
            elif "phone" in user_input.lower():
                category = "phone"

            if category:
                if "minimum price" in user_input.lower():
                    query = "SELECT model, price FROM products WHERE category = %s ORDER BY price ASC LIMIT 1;"
                elif "maximum price" in user_input.lower():
                    query = "SELECT model, price FROM products WHERE category = %s ORDER BY price DESC LIMIT 1;"
                
                cursor.execute(query, (category,))
                result = cursor.fetchone()

                if result:
                    return result[0], result[1]
                else:
                    return None, None

        # Handle queries for products based on specific price limits
        price_conditions = {
            'less than': '<',
            'greater than': '>',
            'below': '<',
            'above': '>'
        }

        price_limit = None
        price_condition = None

        # Check for price conditions in user input
        for condition in price_conditions.keys():
            if condition in user_input.lower():
                price_limit_match = re.search(r'(\d+)', user_input)  # Extract the first number
                if price_limit_match:
                    price_limit = float(price_limit_match.group(1))  # Convert to float
                    price_condition = price_conditions[condition]
                    break  # Exit loop after finding the first match

        if price_limit is not None and category:
            # Construct query based on the condition
            query = f"SELECT model, price FROM products WHERE category = %s AND price {price_condition} %s;"
            print(f"Executing query for list: {query} with category: {category} and price limit: {price_limit}")
            cursor.execute(query, (category, price_limit))
            result = cursor.fetchall()

            if result:
                print(f"Query result: {result}")
                return result, None  # Return the list of filtered products
            else:
                print(f"No results found for the category: {category} with price {price_condition} {price_limit}")
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
def handle_conversation(user_input):
    # Greeting responses
    greetings = ["hi", "hello", "hey"]
    if any(greet in user_input.lower() for greet in greetings):
        return "Hii, what do you want to know?"

    # Handle regular queries (product-related)
    result, price = get_product_price(user_input)
    if result is None:
        return "I'm sorry, but I couldn't find the information you requested."
    elif isinstance(result, list):  # For lists of products
        return "Here is the list of available products."
    else:
        return f"The product is '{result}' priced at ${price:,.2f}."
# Ensure user input is valid for product-related queries
def is_valid_product_query(query):
    # Define keywords that suggest a product-related query
    keywords = ["tablet", "laptop", "phone", "smartphone", "device", "product", "list", "show"]
    
    # Check if the query contains any of the keywords
    return any(keyword in query.lower() for keyword in keywords)
@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    session.pop('chat_history', None)  # Clear the chat history from session
    return render_template("chat.html", chat_history=[])  # Return an empty chat history
@app.route("/", methods=["GET", "POST"])
def chat():
    products = None  # Initialize products variable
    answer = ""

    # Initialize chat history in session if it doesn't exist
    if 'chat_history' not in session:
        session['chat_history'] = []

    if request.method == "POST":
        # Check if it's the clear chat request
        if request.form.get('clear_chat') == 'clear_chat':
            return clear_chat()  # Handle chat clearing

        # Handle regular user input
        user_input = request.form.get('user_input', '').strip()  # Get user input safely

        if user_input:  # Only process if user_input is not empty
            # Define basic conversational queries
            basic_conversation = ["hi", "hello", "how are you", "what's up", "hey"]

            # Check if it's a basic conversational input
            if any(phrase in user_input.lower() for phrase in basic_conversation):
                try:
                    # Log that OpenAI is being used for a basic conversation
                    print(f"User input: {user_input}")
                    print(f"Using OpenAI for a basic conversation response...")

                    # Call OpenAI's ChatCompletion API for basic conversation
                    conversation_prompt = f"The user said: {user_input}. Respond naturally as if you're having a conversation."
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": conversation_prompt}],
                        max_tokens=50  # Limit tokens to keep response short
                    )
                    answer = response['choices'][0]['message']['content'].strip()

                    # Log the OpenAI response
                    print(f"OpenAI response: {answer}")

                except openai.OpenAIError as e:
                    answer = "There was an issue with the OpenAI API. Please try again later."
                    print(f"OpenAIError: {str(e)}")
                except Exception as e:
                    answer = f"An error occurred: {str(e)}"
                    print(f"Error: {str(e)}")

            else:
                # Check if the user input is valid for a product-related query
                if is_valid_product_query(user_input):
                    # For valid product-related queries, check the database first
                    print(f"User input: {user_input}")
                    print(f"Executing database query for product information...")

                    result, price = get_product_price(user_input)

                    if result:  # If we found a product in the database
                        if isinstance(result, list):  # If multiple products are returned
                            products = result  # Store the list of products for rendering in the template
                            answer = "Here is the list of available products:"
                            print(f"Query result: {products}")

                        else:
                            # Provide the result for a single product
                            answer = f"The product is '{result}' priced at ${price:,.2f}."
                            print(f"Query result: ('{result}', {price})")

                    else:
                        # If no product is found in the database, ask for confirmation to use OpenAI API
                        session['awaiting_external_confirmation'] = True
                        answer = "I couldn't find this in the database. Would you like me to search for more information online?"
                        print(f"Database query returned no results. Awaiting user confirmation for external source.")
                
                else:
                    # If the input is too vague for a product query
                    answer = "Please provide more details in your query."
                    print("Vague input detected. Asking user for clarification.")

            # Append the user input and answer to the chat history
            session['chat_history'].append({'user_input': user_input, 'answer': answer})
            session.modified = True  # Mark the session as modified to save changes

        else:
            answer = "Please enter a valid question."

        # Render the template with the user input and answer, and the chat history
        return render_template("chat.html", user_input=user_input, answer=answer, products=products, chat_history=session['chat_history'])

    # Check for confirmation before using external sources
    if 'awaiting_external_confirmation' in session and request.method == "POST":
        confirmation = request.form.get('confirmation')
        if confirmation == 'yes':
            try:
                # Proceed with external source (e.g., OpenAI)
                print("User confirmed. Proceeding with external source.")
                
                openai_prompt = f"User asked: {user_input}. The database does not have this information. Please generate a response based on general product knowledge."
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": openai_prompt}],
                    max_tokens=100  # Increase token limit for more complex queries
                )
                answer = response['choices'][0]['message']['content'].strip()

                # Log the OpenAI response
                print(f"OpenAI response: {answer}")

            except openai.OpenAIError as e:
                answer = "There was an issue with the OpenAI API. Please try again later."
                print(f"OpenAIError: {str(e)}")
            except Exception as e:
                answer = f"An error occurred: {str(e)}"
                print(f"Error: {str(e)}")

            # Append the response from external source
            session['chat_history'].append({'user_input': user_input, 'answer': answer})
            session.modified = True

        # Clear the flag after processing
        session.pop('awaiting_external_confirmation', None)

    return render_template("chat.html", chat_history=session['chat_history'])

if __name__ == "__main__":
    app.run(debug=True)

