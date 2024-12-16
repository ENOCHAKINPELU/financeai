#importing all dependencies
import streamlit as st
import google.generativeai as genai
import os
import pandas as pd
import re

# Configure the Google Gemini AI API key
genai.configure(api_key='AIzaSyCYT1rz4iRaadHKWei_OYm6XTXIQDvRO40')

# Setting model name
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Function definitions (same as in original code)
def load_data_from_file(uploaded_file):
    """Loads and cleans data from a bank statement (CSV or Excel)."""
    try:
        if uploaded_file.name.lower().endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Error: Unsupported file format. Please use a CSV or Excel file.")
            return None
        
        # standardize column names (making them lower case and without spaces)
        df.columns = df.columns.str.lower().str.replace(' ', '_')

        # columns are present, adjust if needed for different bank layouts
        if 'date' not in df.columns or 'description' not in df.columns or 'amount' not in df.columns:
            st.error("Error: The file must have 'date', 'description', and 'amount' columns (or very similar).")
            return None
        
        # Attempt to identify the amount column, looking for common debit/credit descriptions
        amount_column = 'amount'

        # Convert the date column to datetime objects, trying multiple formats
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date']) # Remove rows that couldn't be converted to date time objects

        # Convert the amount column to numeric values
        df[amount_column] = pd.to_numeric(df[amount_column], errors='coerce')
        df = df.dropna(subset=[amount_column]) # Remove rows that couldn't be converted to numeric values


        # Filter out rows that have a debit or credit that is greater than 0
        df = df[df[amount_column] != 0]
        
        transactions = df[['date', 'description', amount_column]].to_dict(orient='records')

        data = {
            "transactions": transactions
        }

        return data
    except FileNotFoundError:
        st.error(f"Error: File not found at")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def get_ai_response(prompt):
    """
    Sends a prompt to the Gemini model and returns the response.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error: {e}")
        return "Sorry, I encountered an error processing your request."

def analyze_spending(data):
    """Analyzes spending habits based on transaction data."""
    transactions = data.get("transactions", [])
    if not transactions:
        return "No transaction data found."
    
    df = pd.DataFrame(transactions)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce') # Make sure amount is numeric
    df = df.dropna(subset=['amount']) # Drop any nans in the amount column

    total_spending = df['amount'].abs().sum() # Get the absolute value for all spending
    
    # Extract categories from the transaction description
    df['category'] = df['description'].apply(extract_category)

    # Apply abs after grouping, summing and using the abs() function
    category_spending = df.groupby('category')['amount'].sum().abs()

    analysis = f"Total spending: ${total_spending:.2f}\n"
    analysis += "Spending per category:\n"
    analysis += category_spending.to_string()

    return analysis

def extract_category(description):
  """Extracts a category from the transaction description using regex"""
  categories = {
      "groceries": r".*(grocery|supermarket|food|market).*",
      "utilities": r".*(electricity|gas|water|internet|phone).*",
      "dining": r".*(restaurant|cafe|bar|food).*",
      "shopping": r".*(store|shop|retail|clothing).*",
      "transportation": r".*(transport|train|bus|taxi|uber|lyft|gas).*",
      "entertainment": r".*(movie|concert|theater|game|amusement).*",
      "subscription": r".*(subscription|netflix|spotify|hulu).*",
      "travel": r".*(airline|hotel|travel).*",
  }

  description = description.lower()
  for category, pattern in categories.items():
    if re.match(pattern, description):
      return category
  return "other"

def get_budget_advice(data):
    """Provides general budgeting advice based on the data."""
    
    advice = "General budgeting tips:\n"
    advice += "- Consider using the 50/30/20 rule (50% needs, 30% wants, 20% savings)\n"
    advice += "- Identify areas where you can potentially cut back or increase savings.\n"
    
    return advice

def get_investment_suggestions():
    """Provides general investment suggestions."""

    advice = "General investment tips:\n"
    advice += "- Diversify your investments across different asset classes to reduce risk.\n"
    advice += "- Consider investment opportunities such as stocks, bonds, ETFs, and mutual funds.\n"
    advice += "- Note: I can only provide general information on this topic. Always consult with a financial professional for personalized advice.\n"
    return advice

# Streamlit UI
def main():
    st.title("AI Personal Finance Assistant")

    # Initialize session state for login status, chat history and the data
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'chat_history' not in st.session_state:
      st.session_state.chat_history = []
    if 'data' not in st.session_state:
        st.session_state.data = None

    # Authentication logic
    if not st.session_state.logged_in:
        with st.form(key='login_form'):
            st.header("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

        if login_button:
          if username == "user" and password == "password": # Basic authentication.  For more complex, use a database
            st.session_state.logged_in = True
            st.success("Logged in successfully!")
            st.rerun()
          else:
            st.error("Incorrect username or password.")

    else:

        # File upload
        uploaded_file = st.file_uploader("Upload your bank statement (CSV or Excel)", type=["csv", "xls", "xlsx"])
        if uploaded_file:
            # Get the file name
            file_name = uploaded_file.name
            
            # Load the data to the session state
            st.session_state.data = load_data_from_file(uploaded_file)

        # Only create the chat interface if data has been loaded
        if st.session_state.data:
          
          # Display existing chat history
          for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

          # Chat input
          if prompt := st.chat_input("Ask me about your finances. Enter 'help' to see available commands."):
              with st.chat_message("user"):
                  st.write(prompt)
              
              st.session_state.chat_history.append({"role": "user", "content": prompt})
              
              # Command parsing
              if prompt.lower() == "help":
                  response_text = "Available commands: 'analyze', 'budget', 'invest', 'exit'"

              elif prompt.lower() == "analyze":
                  response_text = analyze_spending(st.session_state.data)
                
              elif prompt.lower() == "budget":
                  response_text = get_budget_advice(st.session_state.data)
                
              elif prompt.lower() == "invest":
                  response_text = get_investment_suggestions()
              
              elif prompt.lower() == "exit":
                 response_text = "Exiting the chat."
                 st.session_state.logged_in = False # Reset login for next use
                 st.rerun()
                
              else:
                  ai_prompt = f"""
                  You are an AI Personal Finance Assistant. Your goal is to give helpful 
                  and practical advice for personal finance topics.
                  Remember, do not provide any specific advice without asking for a users
                  risk level or financial goals, but give helpful suggestions for finding resources.
                  If the user asks about saving and investment, inform the user that you can only
                  provide general information on these topics and they should consult with a
                  financial professional.

                  Here is the user's financial data: {st.session_state.data}
                  User's Question: {prompt}
                  """
                  response_text = get_ai_response(ai_prompt)

              with st.chat_message("assistant"):
                  st.write(response_text)

              st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        else:
          st.info("Please upload your bank statement to start.")


if __name__ == "__main__":
    main()